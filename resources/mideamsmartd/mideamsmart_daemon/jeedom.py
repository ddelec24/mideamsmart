"""Communication with Jeedom.

Jeedom -> daemon: one JSON object per TCP connection, on a single line,
carrying the plugin apikey and an "action" key (see JeedomSocketServer).
Daemon -> Jeedom: JSON posted to core/php/jeemideamsmart.php (see JeedomCallback).
"""

import asyncio
import hmac
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

_LOGGER = logging.getLogger(__name__)

LOG_FORMAT = '[%(asctime)-15s][%(levelname)s] : %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Jeedom log levels (log::convertLogLevel) to Python levels
LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'notice': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'alert': logging.CRITICAL,
    'emergency': logging.CRITICAL,
    'none': logging.CRITICAL + 10,
}

SENSITIVE_KEYS = frozenset({'apikey', 'token', 'key', 'password', 'cloudPassword', 'cloudAccount'})
MAX_MESSAGE_SIZE = 1024 * 1024
READ_TIMEOUT = 10


def setup_logging(level: str) -> None:
    python_level = LOG_LEVELS.get(level, logging.ERROR)
    logging.basicConfig(level=python_level, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    # httpx logs the requested URLs, which contain the apikey: keep it quiet
    for library in ('httpx', 'httpcore'):
        logging.getLogger(library).setLevel(max(python_level, logging.WARNING))
    # The device libraries are verbose: their info logs are only shown in debug mode
    for library in ('msmart', 'midealocal'):
        logging.getLogger(library).setLevel(python_level if python_level <= logging.DEBUG else max(python_level, logging.WARNING))


def redact(value: Any) -> Any:
    """Copy of a message where the secrets are masked, for logging."""
    if isinstance(value, dict):
        return {k: ('***' if k in SENSITIVE_KEYS and v else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def merge_dict(target: dict, source: dict) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_dict(target[key], value)
        else:
            target[key] = value


MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]


class JeedomSocketServer:
    """TCP server receiving the messages sent by the plugin (mideamsmart::sendToDaemon)."""

    def __init__(self, host: str, port: int, apikey: str, handler: MessageHandler) -> None:
        self._host = host
        self._port = port
        self._apikey = apikey
        self._handler = handler
        self._server: asyncio.Server | None = None
        self._tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._on_connection, self._host, self._port, limit=MAX_MESSAGE_SIZE)
        _LOGGER.info('Listening on %s:%s', self._host, self._port)

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _on_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            line = await asyncio.wait_for(reader.readline(), READ_TIMEOUT)
        except (TimeoutError, ValueError, ConnectionError) as error:
            _LOGGER.warning('Unable to read the message from Jeedom: %s', error)
            return
        finally:
            writer.close()
        message = self.parse_message(line)
        if message is None:
            return
        # Handlers may be slow (cloud, network): never block the socket
        task = asyncio.create_task(self._run_handler(message))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def parse_message(self, line: bytes) -> dict[str, Any] | None:
        try:
            message = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            _LOGGER.error('Invalid message received from Jeedom (not JSON)')
            return None
        if not isinstance(message, dict):
            _LOGGER.error('Invalid message received from Jeedom (not an object)')
            return None
        if not hmac.compare_digest(str(message.pop('apikey', '')), self._apikey):
            _LOGGER.error('Message received with an invalid apikey, ignored')
            return None
        _LOGGER.debug('Message received: %s', redact(message))
        return message

    async def _run_handler(self, message: dict[str, Any]) -> None:
        try:
            await self._handler(message)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception('Error while handling the action "%s"', message.get('action'))


class JeedomCallback:
    """Sends data to Jeedom through the plugin callback (core/php/jeemideamsmart.php).

    Device values are merged and sent together every `cycle` seconds,
    other messages are sent immediately.
    """

    def __init__(self, url: str, apikey: str, cycle: float = 0.5, retry: int = 3) -> None:
        self._url = url
        self._apikey = apikey
        self._cycle = cycle
        self._retry = retry
        self._pending_values: dict[str, dict[str, Any]] = {}
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30, connect=5), verify=False)
        self._flush_task: asyncio.Task | None = None

    async def test(self) -> bool:
        try:
            response = await self._client.get(self._url, params={'apikey': self._apikey, 'test': 1})
        except httpx.HTTPError as error:
            _LOGGER.error('Unable to reach Jeedom on %s: %s. Check the network configuration of Jeedom', self._url, error)
            return False
        if response.status_code != 200 or response.text.strip() != 'OK':
            _LOGGER.error('Unexpected answer from Jeedom on %s: HTTP %s %s', self._url, response.status_code, response.text[:200])
            return False
        return True

    def start(self) -> None:
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_loop())

    async def close(self) -> None:
        if self._flush_task is not None:
            self._flush_task.cancel()
            await asyncio.gather(self._flush_task, return_exceptions=True)
            self._flush_task = None
        await self.flush()
        await self._client.aclose()

    def add_values(self, eq_logic_id: int | str, values: dict[str, Any]) -> None:
        """Queues command values ({logicalId: value}) of an equipment."""
        merge_dict(self._pending_values.setdefault(str(eq_logic_id), {}), values)

    async def flush(self) -> None:
        if not self._pending_values:
            return
        values, self._pending_values = self._pending_values, {}
        await self.send({'action': 'deviceValues', 'devices': values})

    async def send(self, message: dict[str, Any]) -> bool:
        _LOGGER.debug('Sending to Jeedom: %s', redact(message))
        for attempt in range(1, self._retry + 1):
            try:
                response = await self._client.post(self._url, params={'apikey': self._apikey}, json=message)
                if response.status_code == 200:
                    return True
                _LOGGER.warning('Jeedom answered HTTP %s (attempt %s/%s)', response.status_code, attempt, self._retry)
            except httpx.HTTPError as error:
                _LOGGER.warning('Unable to send data to Jeedom: %s (attempt %s/%s)', error, attempt, self._retry)
            if attempt < self._retry:
                await asyncio.sleep(0.5 * attempt)
        _LOGGER.error('Data not sent to Jeedom after %s attempts: %s', self._retry, message.get('action'))
        return False

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(self._cycle)
            try:
                await self.flush()
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception('Error while sending values to Jeedom')

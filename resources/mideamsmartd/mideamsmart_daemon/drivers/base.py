"""Common behavior of the device drivers: polling, online state, value publishing, commands."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from ..devices import DeviceConfig

_LOGGER = logging.getLogger(__name__)

# Polling interval multiplier while the appliance does not answer, and its limit
OFFLINE_BACKOFF_FACTOR = 2
MAX_OFFLINE_INTERVAL = 300
# All values are sent again periodically, even unchanged, so that Jeedom stays in sync
FULL_REFRESH_INTERVAL = 600

ValuesCallback = Callable[[int, dict[str, Any]], None]
EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


class CommandError(Exception):
    """Command refused before reaching the appliance, `reason` is sent to Jeedom."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def normalize(value: Any) -> Any:
    """Converts a library value into a JSON value for Jeedom (enum -> lowercase name, bool -> 0/1)."""
    if isinstance(value, bool):
        return 1 if value else 0
    if hasattr(value, 'name') and isinstance(getattr(value, 'name'), str):
        return value.name.lower()
    return value


class BaseDriver:
    """One appliance: polls its state and applies the commands sent by Jeedom.

    Subclasses implement connect(), refresh_state(), read_values(), read_capabilities() and
    the per-command coroutines returned by command_handlers().
    """

    def __init__(self, config: DeviceConfig, publish_values: ValuesCallback, send_event: EventCallback) -> None:
        self.config = config
        self._publish_values = publish_values
        self._send_event = send_event
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._wake_up = asyncio.Event()
        self._online: bool | None = None
        self._last_values: dict[str, Any] = {}
        self._last_full_publish = 0.0
        self._capabilities_sent: dict[str, Any] | None = None

    # --- To implement -------------------------------------------------------

    async def connect(self) -> None:
        """Prepares the connection (authentication, capabilities). May be called again after a failure."""
        raise NotImplementedError

    async def refresh_state(self) -> bool:
        """Reads the appliance state, returns whether it answered."""
        raise NotImplementedError

    def read_values(self) -> dict[str, Any]:
        """Current values indexed by command logicalId (None = unknown, not sent)."""
        raise NotImplementedError

    def read_capabilities(self) -> dict[str, Any]:
        """Capabilities used by Jeedom to create the commands."""
        raise NotImplementedError

    def command_handlers(self) -> dict[str, Callable[[Any], Awaitable[None]]]:
        raise NotImplementedError

    async def close(self) -> None:
        """Releases the connection."""

    # --- Life cycle ---------------------------------------------------------

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name=f'driver-{self.config.eq_logic_id}')

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        try:
            await self.close()
        except Exception:
            _LOGGER.exception('[%s] Error while closing the connection', self.config.label)

    def request_refresh(self) -> None:
        self._wake_up.set()

    async def _run(self) -> None:
        interval = self.config.polling_interval
        connected = False
        while True:
            try:
                async with self._lock:
                    if not connected:
                        await self.connect()
                        connected = True
                    online = await self.refresh_state()
                await self._after_refresh(online)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                _LOGGER.warning('[%s] Communication error: %s', self.config.label, error)
                _LOGGER.debug('[%s] Error details', self.config.label, exc_info=True)
                connected = False
                online = False
                await self._after_refresh(False)
            if online:
                interval = self.config.polling_interval
            else:
                interval = min(max(interval, self.config.polling_interval) * OFFLINE_BACKOFF_FACTOR, MAX_OFFLINE_INTERVAL)
            self._wake_up.clear()
            try:
                await asyncio.wait_for(self._wake_up.wait(), interval)
            except TimeoutError:
                pass

    async def _after_refresh(self, online: bool) -> None:
        if online != self._online:
            if online:
                _LOGGER.info('[%s] Appliance online (%s:%s)', self.config.label, self.config.ip_address, self.config.port)
            else:
                _LOGGER.warning('[%s] Appliance not answering (%s:%s)', self.config.label, self.config.ip_address, self.config.port)
            self._online = online
            self._publish({'online': 1 if online else 0}, force=True)
        if not online:
            return
        capabilities = self.read_capabilities()
        if capabilities != self._capabilities_sent:
            await self._send_event({'action': 'deviceCapabilities', 'eqLogicId': self.config.eq_logic_id,
                                    'deviceType': self.config.device_type, 'capabilities': capabilities})
            self._capabilities_sent = capabilities
        force = time.monotonic() - self._last_full_publish > FULL_REFRESH_INTERVAL
        self._publish(self.read_values(), force=force)
        if force:
            self._last_full_publish = time.monotonic()

    def _publish(self, values: dict[str, Any], force: bool = False) -> None:
        changed = {}
        for logical_id, value in values.items():
            value = normalize(value)
            if value is None:
                continue
            if force or self._last_values.get(logical_id) != value:
                changed[logical_id] = value
                self._last_values[logical_id] = value
        if changed:
            self._publish_values(self.config.eq_logic_id, changed)

    def resend_values(self) -> None:
        """Sends every value again at the next refresh (after commands were created in Jeedom)."""
        self._last_values.clear()
        self.request_refresh()

    def resend_capabilities(self) -> None:
        """Sends the capabilities again at the next refresh (commands recreation asked by the user)."""
        self._capabilities_sent = None
        self.request_refresh()

    # --- Commands -----------------------------------------------------------

    async def execute(self, command: str, value: Any) -> None:
        if command == 'refresh':
            self.request_refresh()
            return
        handler = self.command_handlers().get(command)
        if handler is None:
            raise CommandError('unknownCommand')
        async with self._lock:
            await handler(value)
            online = await self.refresh_state()
        await self._after_refresh(online)
        if not online:
            # msmart-ng does not raise when the appliance does not answer
            raise CommandError('deviceOffline')

"""Daemon life cycle and dispatch of the actions sent by Jeedom."""

import asyncio
import logging
import os
import signal
from typing import Any

from .devices import DeviceManager
from .jeedom import JeedomCallback, JeedomSocketServer

_LOGGER = logging.getLogger(__name__)


class Daemon:

    def __init__(self, *, socket_host: str, socket_port: int, callback_url: str, apikey: str,
                 pid_file: str, cycle: float) -> None:
        self._pid_file = pid_file
        self._callback = JeedomCallback(callback_url, apikey, cycle)
        self._socket_server = JeedomSocketServer(socket_host, socket_port, apikey, self.handle_message)
        self._device_manager = DeviceManager()
        self._stop_event = asyncio.Event()
        self._handlers = {
            'setDevices': self._on_set_devices,
            'updateDevice': self._on_update_device,
            'removeDevice': self._on_remove_device,
            'stop': self._on_stop,
        }

    @property
    def device_manager(self) -> DeviceManager:
        return self._device_manager

    async def run(self) -> int:
        """Runs until SIGTERM/SIGINT, returns the process exit code."""
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(signum, self.stop, signum)
        self._write_pid()
        try:
            if not await self._callback.test():
                return 1
            try:
                await self._socket_server.start()
            except OSError as error:
                _LOGGER.error('Unable to open the daemon port: %s', error)
                return 1
            self._callback.start()
            await self._callback.send({'action': 'daemonStarted', 'pid': os.getpid()})
            _LOGGER.info('Daemon started')
            await self._stop_event.wait()
            return 0
        finally:
            await self._shutdown()

    def stop(self, signum: int | None = None) -> None:
        if signum is not None:
            _LOGGER.info('Signal %s received, stopping', signal.Signals(signum).name)
        self._stop_event.set()

    async def handle_message(self, message: dict[str, Any]) -> None:
        action = message.get('action')
        handler = self._handlers.get(action)
        if handler is None:
            _LOGGER.warning('Unknown action received from Jeedom: %s', action)
            return
        await handler(message)

    async def _on_set_devices(self, message: dict[str, Any]) -> None:
        self._device_manager.set_devices(message.get('devices') or [])

    async def _on_update_device(self, message: dict[str, Any]) -> None:
        device = message.get('device')
        if isinstance(device, dict):
            self._device_manager.update_device(device)

    async def _on_remove_device(self, message: dict[str, Any]) -> None:
        if 'eqLogicId' in message:
            self._device_manager.remove_device(message['eqLogicId'])

    async def _on_stop(self, message: dict[str, Any]) -> None:
        _LOGGER.info('Stop requested by Jeedom')
        self.stop()

    async def _shutdown(self) -> None:
        _LOGGER.info('Stopping the daemon')
        for step in (self._socket_server.close, self._callback.close):
            try:
                await step()
            except Exception:
                _LOGGER.exception('Error while stopping the daemon')
        self._remove_pid()
        _LOGGER.info('Daemon stopped')

    def _write_pid(self) -> None:
        directory = os.path.dirname(self._pid_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self._pid_file, 'w', encoding='ascii') as pid_file:
            pid_file.write(str(os.getpid()))

    def _remove_pid(self) -> None:
        try:
            os.remove(self._pid_file)
        except FileNotFoundError:
            pass
        except OSError as error:
            _LOGGER.warning('Unable to remove the PID file %s: %s', self._pid_file, error)

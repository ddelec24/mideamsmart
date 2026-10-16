"""Daemon life cycle and dispatch of the actions sent by Jeedom."""

import asyncio
import logging
import os
import signal
import sys
from typing import Any

from .cloud import CloudGuard
from .devices import DeviceManager
from .drivers import CommandError
from .jeedom import JeedomCallback, JeedomSocketServer
from .sync import SyncRequest, SyncService
from .watchdog import AddressWatchdog

_LOGGER = logging.getLogger(__name__)


class Daemon:

    def __init__(self, *, socket_host: str, socket_port: int, callback_url: str, apikey: str,
                 pid_file: str, cycle: float) -> None:
        self._pid_file = pid_file
        self._callback = JeedomCallback(callback_url, apikey, cycle)
        self._socket_server = JeedomSocketServer(socket_host, socket_port, apikey, self.handle_message)
        self._device_manager = DeviceManager(self._callback.add_values, self._callback.send)
        self._sync_service = SyncService(CloudGuard())
        self._sync_lock = asyncio.Lock()
        self._watchdog = AddressWatchdog(self._device_manager, self._callback.send)
        self._stop_event = asyncio.Event()
        self._handlers = {
            'setDevices': self._on_set_devices,
            'updateDevice': self._on_update_device,
            'removeDevice': self._on_remove_device,
            'syncDevices': self._on_sync_devices,
            'executeCommand': self._on_execute_command,
            'refreshCapabilities': self._on_refresh_capabilities,
            'getDiagnostic': self._on_get_diagnostic,
            'resendValues': self._on_resend_values,
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
            self._watchdog.start()
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
        self._device_manager.set_broadcast_addresses(message.get('broadcastAddress', ''))
        await self._device_manager.set_devices(message.get('devices') or [])

    async def _on_update_device(self, message: dict[str, Any]) -> None:
        device = message.get('device')
        if isinstance(device, dict):
            await self._device_manager.update_device(device)

    async def _on_remove_device(self, message: dict[str, Any]) -> None:
        if 'eqLogicId' in message:
            await self._device_manager.remove_device(message['eqLogicId'])

    async def _on_execute_command(self, message: dict[str, Any]) -> None:
        eq_logic_id = message.get('eqLogicId')
        command = str(message.get('command') or '')
        driver = self._device_manager.get_driver(eq_logic_id) if eq_logic_id is not None else None
        reason = None
        if driver is None:
            reason = 'deviceNotRunning'
        else:
            _LOGGER.info('[%s] Command %s %s', driver.config.label, command, message.get('value', ''))
            try:
                await driver.execute(command, message.get('value'))
            except CommandError as error:
                reason = error.reason
            except Exception as error:
                _LOGGER.warning('[%s] Command %s failed: %s', driver.config.label, command, error)
                _LOGGER.debug('Error details', exc_info=True)
                reason = 'communicationError'
        if reason is not None:
            _LOGGER.warning('Command %s refused for the equipment %s: %s', command, eq_logic_id, reason)
            await self._callback.send({'action': 'commandError', 'eqLogicId': eq_logic_id, 'command': command, 'reason': reason})

    async def _on_resend_values(self, message: dict[str, Any]) -> None:
        driver = self._device_manager.get_driver(message.get('eqLogicId', 0))
        if driver is not None:
            driver.resend_values()

    async def _on_get_diagnostic(self, message: dict[str, Any]) -> None:
        eq_logic_id = message.get('eqLogicId', 0)
        driver = self._device_manager.get_driver(eq_logic_id)
        diagnostic = {
            'daemon': {'python': sys.version.split()[0], 'pid': os.getpid(), 'equipments': len(self._device_manager.devices)},
            'driver': driver.diagnostic() if driver is not None else None,
        }
        await self._callback.send({'action': 'deviceDiagnostic', 'eqLogicId': eq_logic_id, 'diagnostic': diagnostic})

    async def _on_refresh_capabilities(self, message: dict[str, Any]) -> None:
        driver = self._device_manager.get_driver(message.get('eqLogicId', 0))
        if driver is not None:
            driver.resend_capabilities()

    async def _on_sync_devices(self, message: dict[str, Any]) -> None:
        request = SyncRequest.from_jeedom(message)
        if self._sync_lock.locked():
            _LOGGER.warning('A synchronization is already running')
            await self._callback.send({'action': 'syncResult', 'failed': 'alreadyRunning', 'onlyDeviceId': message.get('onlyDeviceId')})
            return
        async with self._sync_lock:
            _LOGGER.info('Synchronization requested%s', f' for the appliance {request.only_device_id}' if request.only_device_id else '')

            async def progress(step: str) -> None:
                await self._callback.send({'action': 'syncProgress', 'step': step})

            try:
                result = await self._sync_service.run(request, progress)
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception('Synchronization failed')
                result = {'failed': 'internalError', 'onlyDeviceId': message.get('onlyDeviceId')}
            await self._callback.send({'action': 'syncResult', **result})

    async def _on_stop(self, message: dict[str, Any]) -> None:
        _LOGGER.info('Stop requested by Jeedom')
        self.stop()

    async def _shutdown(self) -> None:
        _LOGGER.info('Stopping the daemon')
        for step in (self._socket_server.close, self._watchdog.stop, self._device_manager.close, self._callback.close):
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

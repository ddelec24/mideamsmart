"""Dehumidifier driver (type 0xA1), based on midea-local.

midea-local devices run their own thread: connection, reconnection backoff, periodic
query and push of the changes through register_update(). This driver relays these
updates to the asyncio loop and runs the (blocking) commands in a worker thread.
"""

import asyncio
import logging
from typing import Any

from midealocal.const import ProtocolVersion
from midealocal.devices import device_selector
from midealocal.devices.a1 import DeviceAttributes as A1

from .base import BaseDriver, CommandError
from .msmart_driver import to_float

_LOGGER = logging.getLogger(__name__)

MIN_TARGET_HUMIDITY = 35
MAX_TARGET_HUMIDITY = 85
# Delay for the appliance to confirm a Set message
SET_CONFIRMATION_TIMEOUT = 10

# midea-local attribute -> Jeedom command logicalId
VALUES = {
    A1.power: 'power',
    A1.mode: 'mode',
    A1.fan_speed: 'fanSpeed',
    A1.target_humidity: 'targetHumidity',
    A1.current_humidity: 'currentHumidity',
    A1.current_temperature: 'currentTemperature',
    A1.tank: 'tankLevel',
    A1.tank_full: 'tankFull',
    A1.water_level_set: 'waterLevelSet',
    A1.swing: 'swing',
    A1.child_lock: 'childLock',
    A1.anion: 'anion',
    A1.pump: 'pump',
    A1.filter_cleaning_reminder: 'filterCleaningReminder',
}


class A1Driver(BaseDriver):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.device = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._update_lock = asyncio.Lock()

    def create_device(self):
        config = self.config
        return device_selector(
            name=config.name or str(config.device_id),
            device_id=config.device_id,
            device_type=0xA1,
            ip_address=config.ip_address,
            port=config.port,
            token=config.token,
            key=config.key,
            device_protocol=ProtocolVersion.V3 if config.protocol_version >= 3 else ProtocolVersion.V2,
            model='',
            subtype=0,
            customize='',
        )

    # --- Life cycle: the midea-local thread replaces the polling loop -------

    def start(self) -> None:
        config = self.config
        if not config.ip_address:
            _LOGGER.error('[%s] No IP address configured', config.label)
            self._publish({'online': 0}, force=True)
            return
        if config.protocol_version >= 3 and (not config.token or not config.key):
            _LOGGER.error('[%s] V3 appliance without token/key: synchronize it or enter them', config.label)
            self._publish({'online': 0}, force=True)
            return
        self._loop = asyncio.get_running_loop()
        self.device = self.create_device()
        self.device.set_refresh_interval(config.polling_interval)
        self.device.set_attribute(A1.prompt_tone, config.beep)
        self.device.register_update(self._on_device_update)
        self.device.open()
        _LOGGER.info('[%s] Connecting to %s:%s', config.label, config.ip_address, config.port)

    async def stop(self) -> None:
        if self.device is not None:
            self.device.unregister_update(self._on_device_update)
            # close() only stops the loop and the socket, the thread ends by itself
            await asyncio.to_thread(self.device.close)
            self.device = None

    def _on_device_update(self, status: dict[str, Any]) -> None:
        """Called from the midea-local thread."""
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(lambda: asyncio.ensure_future(self._handle_update(dict(status))))

    async def _handle_update(self, status: dict[str, Any]) -> None:
        # The updates are handled one after the other, in their arrival order
        async with self._update_lock:
            if self.device is None:
                return
            if 'available' in status:
                await self._after_refresh(bool(status['available']))
            elif self.device.available:
                await self._after_refresh(True)

    def request_refresh(self) -> None:
        # Only the midea-local thread may use the socket for queries: ask it to query at its
        # next loop iteration (it waits up to 10 s for incoming data between iterations).
        if self.device is not None:
            self.device._previous_refresh = 0  # pylint: disable=protected-access

    # --- Capabilities and values --------------------------------------------

    def read_capabilities(self) -> dict[str, Any]:
        device = self.device
        features = ['targetHumidity', 'swing', 'childLock', 'anion', 'waterLevelSet']
        if device.capabilities.get('pump'):
            features.append('pump')
        return {
            'complete': True,
            'minTargetHumidity': MIN_TARGET_HUMIDITY,
            'maxTargetHumidity': MAX_TARGET_HUMIDITY,
            'features': features,
            'enums': {
                'mode': list(device.modes),
                'fanSpeed': [speed for speed in device.fan_speeds if speed != 'off'],
                'waterLevelSet': list(device.water_level_sets),
            },
        }

    def read_values(self) -> dict[str, Any]:
        attributes = self.device.attributes
        values = {logical_id: attributes.get(str(attribute)) for attribute, logical_id in VALUES.items()}
        if values['waterLevelSet'] is not None:
            values['waterLevelSet'] = str(values['waterLevelSet'])
        return values

    # --- Commands -----------------------------------------------------------

    async def execute(self, command: str, value: Any) -> None:
        if command == 'refresh':
            self.request_refresh()
            return
        handler = self.command_handlers().get(command)
        if handler is None:
            raise CommandError('unknownCommand')
        if self.device is None or not self.device.available:
            raise CommandError('deviceOffline')
        async with self._lock:
            await handler(value)

    async def _set(self, attribute: str, value: Any) -> None:
        # set_attribute() sends on the socket: blocking call. The appliance answers with
        # its new state, which comes back through the update callback.
        await asyncio.to_thread(self.device.set_attribute, attribute, value)

    async def _wait_attribute(self, attribute: str, value: Any, timeout: float = SET_CONFIRMATION_TIMEOUT) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while self.device.attributes.get(str(attribute)) != value:
            if loop.time() > deadline:
                raise CommandError('deviceOffline')
            await asyncio.sleep(0.1)

    async def set_mode(self, value: Any) -> None:
        mode = str(value).lower()
        if mode not in self.device.modes:
            raise CommandError('unsupportedValue')
        if not self.device.attributes.get(str(A1.power)):
            await self._set(A1.power, True)
            # Each Set message is built from the known attributes: wait for the appliance to
            # confirm the power on, otherwise the mode message would turn it off again
            await self._wait_attribute(A1.power, True)
        await self._set(A1.mode, mode)

    async def set_fan_speed(self, value: Any) -> None:
        speed = str(value).lower()
        if speed not in self.device.fan_speeds:
            raise CommandError('unsupportedValue')
        await self._set(A1.fan_speed, speed)

    async def set_target_humidity(self, value: Any) -> None:
        humidity = int(min(max(to_float(value), MIN_TARGET_HUMIDITY), MAX_TARGET_HUMIDITY))
        await self._set(A1.target_humidity, humidity)

    async def set_water_level(self, value: Any) -> None:
        level = str(value)
        if level not in self.device.water_level_sets:
            raise CommandError('unsupportedValue')
        await self._set(A1.water_level_set, level)

    async def reset_filter(self, value: Any) -> None:
        await asyncio.to_thread(self.device.reset_filter)

    def command_handlers(self) -> dict:
        handlers = {
            'on': lambda value: self._set(A1.power, True),
            'off': lambda value: self._set(A1.power, False),
            'setMode': self.set_mode,
            'setFanSpeed': self.set_fan_speed,
            'setTargetHumidity': self.set_target_humidity,
            'setWaterLevelSet': self.set_water_level,
            'resetFilter': self.reset_filter,
        }
        for logical_id, attribute in (('swing', A1.swing), ('childLock', A1.child_lock), ('anion', A1.anion), ('pump', A1.pump)):
            handlers[f'{logical_id}On'] = lambda value, attribute=attribute: self._set(attribute, True)
            handlers[f'{logical_id}Off'] = lambda value, attribute=attribute: self._set(attribute, False)
        return handlers

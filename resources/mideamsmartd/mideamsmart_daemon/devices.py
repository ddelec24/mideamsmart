"""Configuration of the equipments managed by the daemon."""

import logging
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)

DEFAULT_DEVICE_PORT = 6444
DEFAULT_POLLING_INTERVAL = 30
MIN_POLLING_INTERVAL = 10


class DeviceConfigError(ValueError):
    pass


@dataclass(frozen=True)
class DeviceConfig:
    """Equipment configuration sent by Jeedom (mideamsmart::getDaemonConfig)."""

    eq_logic_id: int
    device_id: int
    device_type: str
    name: str = ''
    ip_address: str = ''
    port: int = DEFAULT_DEVICE_PORT
    protocol_version: int = 3
    token: str = field(default='', repr=False)
    key: str = field(default='', repr=False)
    polling_interval: int = DEFAULT_POLLING_INTERVAL
    beep: bool = True
    temperature_step: float = 1.0
    energy: bool = False
    energy_format: str = 'bcd'
    energy_scale: float = 1.0

    @classmethod
    def from_jeedom(cls, data: dict[str, Any]) -> 'DeviceConfig':
        try:
            eq_logic_id = int(data['eqLogicId'])
            device_id = int(str(data.get('deviceId', '')).strip() or 0)
        except (KeyError, TypeError, ValueError) as error:
            raise DeviceConfigError(f'invalid equipment or device identifier: {error}') from error
        try:
            port = int(data.get('port') or DEFAULT_DEVICE_PORT)
            protocol_version = int(data.get('protocolVersion') or 3)
            polling_interval = max(MIN_POLLING_INTERVAL, int(data.get('pollingInterval') or DEFAULT_POLLING_INTERVAL))
            temperature_step = 0.5 if float(data.get('temperatureStep') or 1) == 0.5 else 1.0
            energy_scale = float(data.get('energyScale') or 1)
        except (TypeError, ValueError) as error:
            raise DeviceConfigError(f'invalid numeric value for equipment {eq_logic_id}: {error}') from error
        return cls(
            eq_logic_id=eq_logic_id,
            device_id=device_id,
            device_type=str(data.get('deviceType', '')).upper(),
            name=str(data.get('name', '')),
            ip_address=str(data.get('ipAddress', '')).strip(),
            port=port,
            protocol_version=protocol_version,
            token=str(data.get('token', '')).strip(),
            key=str(data.get('key', '')).strip(),
            polling_interval=polling_interval,
            beep=bool(int(data.get('beep', 1) or 0)),
            temperature_step=temperature_step,
            energy=bool(int(data.get('energy', 0) or 0)),
            energy_format='binary' if data.get('energyFormat') == 'binary' else 'bcd',
            energy_scale=energy_scale,
        )

    @property
    def label(self) -> str:
        return f'{self.name or self.device_id} [{self.eq_logic_id}]'


class DeviceManager:
    """Keeps the enabled equipments, indexed by eqLogic id, and runs their drivers."""

    def __init__(self, publish_values=None, send_event=None) -> None:
        self._devices: dict[int, DeviceConfig] = {}
        self._drivers: dict[int, Any] = {}
        self._publish_values = publish_values
        self._send_event = send_event
        self.broadcast_addresses: tuple[str, ...] = ()

    @property
    def devices(self) -> dict[int, DeviceConfig]:
        return dict(self._devices)

    @property
    def drivers(self) -> dict[int, Any]:
        return dict(self._drivers)

    def set_broadcast_addresses(self, value: str) -> None:
        self.broadcast_addresses = tuple(address.strip() for address in str(value or '').split(',') if address.strip())

    def get_driver(self, eq_logic_id: int):
        return self._drivers.get(int(eq_logic_id))

    async def set_devices(self, devices: list[dict[str, Any]]) -> None:
        """Replaces the whole list (sent by Jeedom when the daemon starts)."""
        configs = {}
        for data in devices:
            try:
                config = DeviceConfig.from_jeedom(data)
            except DeviceConfigError as error:
                _LOGGER.error('Equipment ignored: %s', error)
                continue
            configs[config.eq_logic_id] = config
        for eq_logic_id in set(self._devices) - set(configs):
            await self.remove_device(eq_logic_id)
        for config in configs.values():
            await self._store(config)
        _LOGGER.info('%s equipment(s) configured', len(self._devices))

    async def update_device(self, data: dict[str, Any]) -> None:
        try:
            config = DeviceConfig.from_jeedom(data)
        except DeviceConfigError as error:
            _LOGGER.error('Equipment ignored: %s', error)
            return
        await self._store(config)

    async def remove_device(self, eq_logic_id: int) -> None:
        eq_logic_id = int(eq_logic_id)
        await self._stop_driver(eq_logic_id)
        config = self._devices.pop(eq_logic_id, None)
        if config is not None:
            _LOGGER.info('Equipment %s removed', config.label)

    async def close(self) -> None:
        for eq_logic_id in list(self._drivers):
            await self._stop_driver(eq_logic_id)

    async def _store(self, config: DeviceConfig) -> None:
        previous = self._devices.get(config.eq_logic_id)
        if previous == config:
            return
        self._devices[config.eq_logic_id] = config
        _LOGGER.info('Equipment %s %s (type %s, %s:%s)', config.label, 'updated' if previous else 'added',
                     config.device_type or '?', config.ip_address or '?', config.port)
        await self._stop_driver(config.eq_logic_id)
        self._start_driver(config)

    def _start_driver(self, config: DeviceConfig) -> None:
        if self._publish_values is None:
            return
        # Imported here: the drivers load the device libraries, not needed by the tests of this module
        from .drivers import DRIVERS
        driver_class = DRIVERS.get(config.device_type)
        if driver_class is None:
            _LOGGER.warning('Equipment %s: appliance type %s not handled yet', config.label, config.device_type or '?')
            return
        driver = driver_class(config, self._publish_values, self._send_event)
        self._drivers[config.eq_logic_id] = driver
        driver.start()

    async def _stop_driver(self, eq_logic_id: int) -> None:
        driver = self._drivers.pop(eq_logic_id, None)
        if driver is not None:
            await driver.stop()

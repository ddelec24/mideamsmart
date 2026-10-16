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
        )

    @property
    def label(self) -> str:
        return f'{self.name or self.device_id} [{self.eq_logic_id}]'


class DeviceManager:
    """Keeps the configuration of the enabled equipments, indexed by eqLogic id."""

    def __init__(self) -> None:
        self._devices: dict[int, DeviceConfig] = {}

    @property
    def devices(self) -> dict[int, DeviceConfig]:
        return dict(self._devices)

    def set_devices(self, devices: list[dict[str, Any]]) -> None:
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
            self.remove_device(eq_logic_id)
        for config in configs.values():
            self._store(config)
        _LOGGER.info('%s equipment(s) configured', len(self._devices))

    def update_device(self, data: dict[str, Any]) -> None:
        try:
            config = DeviceConfig.from_jeedom(data)
        except DeviceConfigError as error:
            _LOGGER.error('Equipment ignored: %s', error)
            return
        self._store(config)

    def remove_device(self, eq_logic_id: int) -> None:
        config = self._devices.pop(int(eq_logic_id), None)
        if config is not None:
            _LOGGER.info('Equipment %s removed', config.label)

    def _store(self, config: DeviceConfig) -> None:
        previous = self._devices.get(config.eq_logic_id)
        if previous == config:
            return
        self._devices[config.eq_logic_id] = config
        _LOGGER.info('Equipment %s %s (type %s, %s:%s)', config.label, 'updated' if previous else 'added',
                     config.device_type or '?', config.ip_address or '?', config.port)

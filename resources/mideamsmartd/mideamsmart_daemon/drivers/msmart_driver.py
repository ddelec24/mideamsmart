"""Base of the drivers using msmart-ng (AC and CC appliances)."""

import asyncio
import logging
import time
from enum import Enum
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import Any

from msmart.lan import AuthenticationError

from .base import BaseDriver, CommandError, normalize

_LOGGER = logging.getLogger(__name__)

# Delays before asking the capabilities again when the appliance did not return them: the
# answer is often lost when the appliance closes its connection, so the first tries are close
CAPABILITIES_RETRY_MIN = 30
CAPABILITIES_RETRY_MAX = 600
# Delay before trying again a refresh without answer (msmart-ng reconnects meanwhile)
REFRESH_RETRY_DELAY = 2


def library_version(package: str) -> str:
    try:
        return package_version(package)
    except PackageNotFoundError:
        return '?'


def enum_from_code(enum_class: type[Enum], code: Any, allowed: list | None = None) -> Enum:
    """Enum member from its Jeedom code (lowercase name), restricted to the supported values."""
    try:
        member = enum_class[str(code).upper()]
    except KeyError as error:
        raise CommandError('invalidValue') from error
    if allowed is not None and member not in allowed:
        raise CommandError('unsupportedValue')
    return member


def enum_codes(members) -> list[str]:
    return [member.name.lower() for member in members]


def to_float(value: Any) -> float:
    try:
        return float(str(value).replace(',', '.'))
    except (TypeError, ValueError) as error:
        raise CommandError('invalidValue') from error


class MsmartDriver(BaseDriver):
    device_class: type = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.device = None
        self._capabilities_loaded = False
        self._capabilities_attempt = 0.0
        self._capabilities_retry_delay = CAPABILITIES_RETRY_MIN
        self._capabilities_reload = False
        self._capabilities_answers = 0

    async def connect(self) -> None:
        config = self.config
        if not config.ip_address:
            raise RuntimeError('no IP address configured')
        if self.device is None:
            self.device = self.device_class(ip=config.ip_address, device_id=config.device_id, port=config.port)
            # msmart-ng gives no result for get_capabilities(): detect a successful answer
            update_capabilities = self.device._update_capabilities  # pylint: disable=protected-access

            def capabilities_received(response) -> None:
                self._capabilities_loaded = True
                self._capabilities_answers += 1
                update_capabilities(response)

            self.device._update_capabilities = capabilities_received  # pylint: disable=protected-access
            if config.connection_lifetime > 0:
                # Remedy recommended by midea-ac-py for the appliances that close their connection
                self.device.set_max_connection_lifetime(config.connection_lifetime)
        if config.protocol_version >= 3:
            if not config.token or not config.key:
                raise RuntimeError('V3 appliance without token/key: synchronize it or enter them')
            try:
                await self.device.authenticate(config.token, config.key)
            except AuthenticationError as error:
                raise RuntimeError(f'authentication refused, check the token/key ({error})') from error
        await self._load_capabilities()

    async def _load_capabilities(self) -> None:
        self._capabilities_attempt = time.monotonic()
        answers = self._capabilities_answers
        await self.device.get_capabilities()
        if self._capabilities_answers > answers:
            self._capabilities_retry_delay = CAPABILITIES_RETRY_MIN
            _LOGGER.info('[%s] Capabilities: %s', self.config.label, self.device.capabilities_dict())
        elif self._capabilities_loaded:
            # msmart-ng keeps the capabilities received before
            _LOGGER.warning('[%s] Capabilities not returned again by the appliance, previous ones kept', self.config.label)
        else:
            _LOGGER.warning('[%s] Capabilities not returned by the appliance, default ones used (new try in %s s)',
                            self.config.label, self._capabilities_retry_delay)

    async def refresh_state(self) -> bool:
        retry_due = time.monotonic() - self._capabilities_attempt > self._capabilities_retry_delay
        if self._capabilities_reload or (not self._capabilities_loaded and retry_due):
            if not self._capabilities_loaded and not self._capabilities_reload:
                self._capabilities_retry_delay = min(self._capabilities_retry_delay * 2, CAPABILITIES_RETRY_MAX)
            self._capabilities_reload = False
            await self._load_capabilities()
        self._prepare()
        await self.device.refresh()
        if not self.device.online:
            # Usually the appliance closed the connection: one more try on a new connection
            _LOGGER.debug('[%s] No answer, new try in %s s', self.config.label, REFRESH_RETRY_DELAY)
            await asyncio.sleep(REFRESH_RETRY_DELAY)
            await self.device.refresh()
        return self.device.online

    def _prepare(self) -> None:
        """Settings sent with every command: Celsius display, beep option."""
        self.device.fahrenheit = False
        if not hasattr(type(self.device), 'sound') or self.device.sound == self.config.beep:
            return
        if getattr(self.device, 'supports_sound', False):
            self.device.sound = self.config.beep
        else:
            # The sound setter always queues a SOUND properties command, which appliances without
            # this capability do not answer (several seconds of timeout). They take the beep from
            # the SetState command, built from the same attribute.
            self.device._sound = self.config.beep  # pylint: disable=protected-access

    async def apply(self) -> None:
        self._prepare()
        await self.device.apply()
        if not self.device.online:
            # The appliance closed the connection before answering: the command may be lost.
            # SetState carries the whole state, sending it again is harmless.
            _LOGGER.debug('[%s] No answer to the command, sending it again in %s s', self.config.label, REFRESH_RETRY_DELAY)
            await asyncio.sleep(REFRESH_RETRY_DELAY)
            self._prepare()
            await self.device.apply()

    async def close(self) -> None:
        if self.device is not None:
            self.device._lan._disconnect()  # pylint: disable=protected-access

    def resend_capabilities(self) -> None:
        """Reads the capabilities again from the appliance (commands update asked by the user)."""
        self._capabilities_reload = True
        super().resend_capabilities()

    def diagnostic(self) -> dict[str, Any]:
        result = super().diagnostic()
        result['library'] = f'msmart-ng {library_version("msmart-ng")}'
        result['capabilitiesReceived'] = self._capabilities_loaded
        if self.device is not None:
            result['deviceCapabilities'] = self.device.serialize_capabilities()
            state = self.device.to_dict()
            for secret in ('token', 'key'):
                state.pop(secret, None)
            result['deviceState'] = {key: normalize(value) for key, value in state.items()}
        return result

    def common_capabilities(self) -> dict[str, Any]:
        device = self.device
        return {
            'complete': self._capabilities_loaded,
            'minTargetTemperature': device.min_target_temperature,
            'maxTargetTemperature': device.max_target_temperature,
            'temperatureStep': self.config.temperature_step,
        }

    # --- Commands shared by AC and CC ---------------------------------------

    async def _power(self, state: bool) -> None:
        self.device.power_state = state
        await self.apply()

    async def set_mode(self, value: Any) -> None:
        self.device.operational_mode = enum_from_code(self.device.OperationalMode, value, self.device.supported_operation_modes)
        self.device.power_state = True
        await self.apply()

    async def set_target_temperature(self, value: Any) -> None:
        temperature = to_float(value)
        temperature = min(max(temperature, self.device.min_target_temperature), self.device.max_target_temperature)
        self.device.target_temperature = round(temperature * 2) / 2
        await self.apply()

    async def set_target_humidity(self, value: Any) -> None:
        self.device.target_humidity = int(min(max(to_float(value), 0), 100))
        await self.apply()

    async def set_fan_speed(self, value: Any) -> None:
        self.device.fan_speed = enum_from_code(self.device.FanSpeed, value, self.device.supported_fan_speeds)
        await self.apply()

    async def set_swing_mode(self, value: Any) -> None:
        self.device.swing_mode = enum_from_code(self.device.SwingMode, value, self.device.supported_swing_modes)
        await self.apply()

    async def set_horizontal_swing_angle(self, value: Any) -> None:
        self.device.horizontal_swing_angle = enum_from_code(self.device.SwingAngle, value)
        await self.apply()

    async def set_vertical_swing_angle(self, value: Any) -> None:
        self.device.vertical_swing_angle = enum_from_code(self.device.SwingAngle, value)
        await self.apply()

    async def set_aux_mode(self, value: Any) -> None:
        self.device.aux_mode = enum_from_code(self.device.AuxHeatMode, value, self.device.supported_aux_modes)
        await self.apply()

    def common_handlers(self) -> dict:
        return {
            'on': lambda value: self._power(True),
            'off': lambda value: self._power(False),
            'setMode': self.set_mode,
            'setTargetTemperature': self.set_target_temperature,
            'setTargetHumidity': self.set_target_humidity,
            'setFanSpeed': self.set_fan_speed,
            'setSwingMode': self.set_swing_mode,
            'setHorizontalSwingAngle': self.set_horizontal_swing_angle,
            'setVerticalSwingAngle': self.set_vertical_swing_angle,
            'setAuxMode': self.set_aux_mode,
        }

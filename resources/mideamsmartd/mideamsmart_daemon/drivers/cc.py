"""Commercial air conditioner driver (type 0xCC), based on msmart-ng."""

from typing import Any

from msmart.device import CommercialAirConditioner as CC

from .base import CommandError
from .msmart_driver import MsmartDriver, enum_codes, enum_from_code

PRESET_NONE = 'none'
PRESET_ECO = 'eco'
PRESET_SILENT = 'silent'
PRESET_SLEEP = 'sleep'


class CcDriver(MsmartDriver):
    device_class = CC

    def _supported_presets(self) -> list[str]:
        device = self.device
        return [preset for preset, supported in (
            (PRESET_NONE, True),
            (PRESET_ECO, device.supports_eco),
            (PRESET_SILENT, device.supports_silent),
            (PRESET_SLEEP, device.supports_sleep),
        ) if supported]

    def read_capabilities(self) -> dict[str, Any]:
        device = self.device
        enums = {
            'mode': enum_codes(device.supported_operation_modes),
            'fanSpeed': enum_codes(device.supported_fan_speeds),
            'swingMode': enum_codes(device.supported_swing_modes),
            'preset': self._supported_presets(),
            'horizontalSwingAngle': enum_codes(CC.SwingAngle.list()),
            'verticalSwingAngle': enum_codes(CC.SwingAngle.list()),
            'purifierMode': enum_codes(device.supported_purifier_modes),
            'auxMode': enum_codes(device.supported_aux_modes),
        }
        features = [feature for feature, supported in (
            ('swingMode', len(device.supported_swing_modes) > 1),
            ('horizontalSwingAngle', device.supports_horizontal_swing_angle),
            ('verticalSwingAngle', device.supports_vertical_swing_angle),
            ('preset', len(enums['preset']) > 1),
            ('humidity', device.supports_humidity),
            ('targetHumidity', device.supports_humidity),
            ('purifierMode', len(device.supported_purifier_modes) > 1),
            ('auxMode', len(device.supported_aux_modes) > 1),
        ) if supported]
        return {**self.common_capabilities(), 'features': features, 'enums': enums}

    def _preset(self) -> str:
        device = self.device
        if device.eco and device.supports_eco:
            return PRESET_ECO
        if device.silent and device.supports_silent:
            return PRESET_SILENT
        if device.sleep and device.supports_sleep:
            return PRESET_SLEEP
        return PRESET_NONE

    def read_values(self) -> dict[str, Any]:
        device = self.device
        return {
            'power': device.power_state,
            'mode': device.operational_mode,
            'targetTemperature': device.target_temperature,
            'indoorTemperature': device.indoor_temperature,
            'outdoorTemperature': device.outdoor_temperature,
            'fanSpeed': device.fan_speed,
            'swingMode': device.swing_mode,
            'horizontalSwingAngle': device.horizontal_swing_angle,
            'verticalSwingAngle': device.vertical_swing_angle,
            'preset': self._preset(),
            'indoorHumidity': device.indoor_humidity,
            'targetHumidity': device.target_humidity,
            'purifierMode': device.purifier,
            'auxMode': device.aux_mode,
        }

    async def set_preset(self, value: Any) -> None:
        preset = str(value).lower()
        if preset not in self._supported_presets():
            raise CommandError('unsupportedValue')
        device = self.device
        device.eco = preset == PRESET_ECO
        device.silent = preset == PRESET_SILENT
        device.sleep = preset == PRESET_SLEEP
        await self.apply()

    async def set_purifier_mode(self, value: Any) -> None:
        self.device.purifier = enum_from_code(CC.PurifierMode, value, self.device.supported_purifier_modes)
        await self.apply()

    def command_handlers(self) -> dict:
        return {
            **self.common_handlers(),
            'setPreset': self.set_preset,
            'setPurifierMode': self.set_purifier_mode,
        }

"""Air conditioner driver (type 0xAC), based on msmart-ng."""

from typing import Any

from msmart.device import AirConditioner as AC

from .base import CommandError
from .msmart_driver import MsmartDriver, enum_codes, enum_from_code, to_float

PRESET_NONE = 'none'
PRESET_SLEEP = 'sleep'
PRESET_FREEZE_PROTECTION = 'freeze_protection'
PRESET_ECO = 'eco'
PRESET_IECO = 'ieco'
PRESET_TURBO = 'turbo'

BREEZE_OFF = 'off'
BREEZE_MODES = ('breeze_away', 'breeze_mild', 'breezeless')

FAN_SPEED_CUSTOM = 'custom'


class AcDriver(MsmartDriver):
    device_class = AC

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._energy_enabled = False

    async def refresh_state(self) -> bool:
        if self.config.energy != self._energy_enabled:
            self.device.enable_energy_usage_requests = self.config.energy
            self._energy_enabled = self.config.energy
        return await super().refresh_state()

    # --- Capabilities -------------------------------------------------------

    def _supported_presets(self) -> list[str]:
        device = self.device
        return [preset for preset, supported in (
            (PRESET_NONE, True),
            (PRESET_SLEEP, True),
            (PRESET_FREEZE_PROTECTION, device.supports_freeze_protection),
            (PRESET_ECO, device.supports_eco),
            (PRESET_IECO, device.supports_ieco),
            (PRESET_TURBO, device.supports_turbo),
        ) if supported]

    def _supported_breeze_modes(self) -> list[str]:
        device = self.device
        modes = [mode for mode, supported in zip(BREEZE_MODES, (
            device.supports_breeze_away, device.supports_breeze_mild, device.supports_breezeless)) if supported]
        return [BREEZE_OFF] + modes if modes else []

    def read_capabilities(self) -> dict[str, Any]:
        device = self.device
        enums = {
            'mode': enum_codes(device.supported_operation_modes),
            'fanSpeed': enum_codes(device.supported_fan_speeds),
            'swingMode': enum_codes(device.supported_swing_modes),
            'preset': self._supported_presets(),
            'breezeMode': self._supported_breeze_modes(),
            'horizontalSwingAngle': enum_codes(AC.SwingAngle.list()),
            'verticalSwingAngle': enum_codes(AC.SwingAngle.list()),
            'cascadeMode': enum_codes(AC.CascadeMode.list()),
            'freshAirFanSpeed': enum_codes(AC.FreshAirFanSpeed.list()),
            'rateSelect': enum_codes(device.supported_rate_selects),
            'auxMode': enum_codes(device.supported_aux_modes),
        }
        features = [feature for feature, supported in (
            ('swingMode', len(device.supported_swing_modes) > 1),
            ('horizontalSwingAngle', device.supports_horizontal_swing_angle),
            ('verticalSwingAngle', device.supports_vertical_swing_angle),
            ('preset', len(enums['preset']) > 1),
            ('breezeMode', bool(enums['breezeMode'])),
            ('customFanSpeed', device.supports_custom_fan_speed),
            ('humidity', device.supports_humidity),
            ('targetHumidity', device.supports_target_humidity),
            ('display', device.supports_display_control),
            ('purifier', device.supports_purifier),
            ('flash', device.supports_flash),
            ('outSilent', device.supports_out_silent),
            ('cascade', device.supports_cascade),
            ('freshAir', device.supports_fresh_air),
            ('rateSelect', len(device.supported_rate_selects) > 1),
            ('auxMode', len(device.supported_aux_modes) > 1),
            ('selfClean', device.supports_self_clean),
            ('filterReminder', device.supports_filter_reminder),
            ('energy', self.config.energy),
        ) if supported]
        return {**self.common_capabilities(), 'features': features, 'enums': enums}

    # --- Values -------------------------------------------------------------

    def _preset(self) -> str:
        device = self.device
        if device.eco and device.supports_eco:
            return PRESET_ECO
        if device.ieco and device.supports_ieco:
            return PRESET_IECO
        if device.turbo and device.supports_turbo:
            return PRESET_TURBO
        if device.freeze_protection and device.supports_freeze_protection:
            return PRESET_FREEZE_PROTECTION
        if device.sleep:
            return PRESET_SLEEP
        return PRESET_NONE

    def _breeze_mode(self) -> str:
        device = self.device
        for mode, active in zip(BREEZE_MODES, (device.breeze_away, device.breeze_mild, device.breezeless)):
            if active:
                return mode
        return BREEZE_OFF

    def _energy_values(self) -> dict[str, Any]:
        if not self.config.energy:
            return {}
        device = self.device
        data_format = AC.EnergyDataFormat.BINARY if self.config.energy_format == 'binary' else AC.EnergyDataFormat.BCD
        scale = self.config.energy_scale

        def scaled(value):
            return None if value is None else round(value * scale, 3)

        return {
            'realTimePower': scaled(device.get_real_time_power_usage(data_format)),
            'totalEnergy': scaled(device.get_total_energy_usage(data_format)),
            'currentEnergy': scaled(device.get_current_energy_usage(data_format)),
        }

    def read_values(self) -> dict[str, Any]:
        device = self.device
        fan_speed = device.fan_speed
        is_named_speed = isinstance(fan_speed, AC.FanSpeed)
        return {
            'power': device.power_state,
            'mode': device.operational_mode,
            'targetTemperature': device.target_temperature,
            'indoorTemperature': device.indoor_temperature,
            'outdoorTemperature': device.outdoor_temperature,
            'fanSpeed': fan_speed if is_named_speed else FAN_SPEED_CUSTOM,
            'fanSpeedPercent': None if fan_speed == AC.FanSpeed.AUTO else int(fan_speed),
            'swingMode': device.swing_mode,
            'horizontalSwingAngle': device.horizontal_swing_angle,
            'verticalSwingAngle': device.vertical_swing_angle,
            'preset': self._preset(),
            'breezeMode': self._breeze_mode(),
            'indoorHumidity': device.indoor_humidity,
            'targetHumidity': device.target_humidity,
            'displayOn': device.display_on,
            'purifier': device.purifier,
            'flash': device.flash,
            'outSilent': device.out_silent,
            'cascadeMode': device.cascade_mode,
            'freshAirFanSpeed': device.fresh_air_fan_speed,
            'rateSelect': device.rate_select,
            'auxMode': device.aux_mode,
            'selfCleanActive': device.self_clean_active,
            'filterAlert': device.filter_alert,
            'defrostActive': device.defrost_active,
            'errorCode': device.error_code,
            **self._energy_values(),
        }

    # --- Commands -----------------------------------------------------------

    async def set_preset(self, value: Any) -> None:
        preset = str(value).lower()
        if preset not in self._supported_presets():
            raise CommandError('unsupportedValue')
        device = self.device
        device.eco = preset == PRESET_ECO
        device.turbo = preset == PRESET_TURBO
        device.freeze_protection = preset == PRESET_FREEZE_PROTECTION
        device.sleep = preset == PRESET_SLEEP
        # Only touch iECO when supported, otherwise it generates a properties command
        if device.supports_ieco:
            device.ieco = preset == PRESET_IECO
        await self.apply()

    async def set_breeze_mode(self, value: Any) -> None:
        mode = str(value).lower()
        if mode not in self._supported_breeze_modes():
            raise CommandError('unsupportedValue')
        device = self.device
        if device.supports_breeze_away:
            device.breeze_away = mode == 'breeze_away'
        if device.supports_breeze_mild:
            device.breeze_mild = mode == 'breeze_mild'
        if device.supports_breezeless:
            device.breezeless = mode == 'breezeless'
        await self.apply()

    async def set_fan_speed_percent(self, value: Any) -> None:
        self.device.fan_speed = int(min(max(to_float(value), 1), 100))
        await self.apply()

    async def toggle_display(self, value: Any) -> None:
        self._prepare()
        await self.device.toggle_display()

    async def start_self_clean(self, value: Any) -> None:
        self._prepare()
        await self.device.start_self_clean()

    async def _set_flag(self, name: str, state: bool) -> None:
        setattr(self.device, name, state)
        await self.apply()

    async def _set_enum(self, name: str, enum_class, value: Any, allowed=None) -> None:
        setattr(self.device, name, enum_from_code(enum_class, value, allowed))
        await self.apply()

    def command_handlers(self) -> dict:
        return {
            **self.common_handlers(),
            'setPreset': self.set_preset,
            'setBreezeMode': self.set_breeze_mode,
            'setFanSpeedPercent': self.set_fan_speed_percent,
            'toggleDisplay': self.toggle_display,
            'startSelfClean': self.start_self_clean,
            'purifierOn': lambda value: self._set_flag('purifier', True),
            'purifierOff': lambda value: self._set_flag('purifier', False),
            'flashOn': lambda value: self._set_flag('flash', True),
            'flashOff': lambda value: self._set_flag('flash', False),
            'outSilentOn': lambda value: self._set_flag('out_silent', True),
            'outSilentOff': lambda value: self._set_flag('out_silent', False),
            'setCascadeMode': lambda value: self._set_enum('cascade_mode', AC.CascadeMode, value),
            'setFreshAirFanSpeed': lambda value: self._set_enum('fresh_air_fan_speed', AC.FreshAirFanSpeed, value),
            'setRateSelect': lambda value: self._set_enum('rate_select', AC.RateSelect, value, self.device.supported_rate_selects),
        }


"""Driver tests against the real msmart-ng device classes, only the network calls are replaced."""

import asyncio
import time
import unittest
from unittest import mock

from msmart.device import AirConditioner as AC
from msmart.device import CommercialAirConditioner as CC

from mideamsmart_daemon.devices import DeviceConfig
from mideamsmart_daemon.drivers.ac import AcDriver
from mideamsmart_daemon.drivers.base import CommandError
from mideamsmart_daemon.drivers.cc import CcDriver

AC_CAPABILITIES = {
    'min_target_temperature': 17,
    'max_target_temperature': 30,
    'supported_modes': ['AUTO', 'COOL', 'DRY', 'HEAT', 'FAN_ONLY'],
    'supported_swing_modes': ['OFF', 'VERTICAL'],
    'supported_fan_speeds': ['AUTO', 'LOW', 'MEDIUM', 'HIGH'],
    'additional_capabilities': ['ECO', 'TURBO', 'FREEZE_PROTECTION', 'DISPLAY_CONTROL', 'BREEZELESS', 'CUSTOM_FAN_SPEED'],
}


class OfflineMixin:
    """Replaces the network calls of the msmart-ng devices."""

    answers = True
    capabilities = None

    def record(self, name):
        self.calls = getattr(self, 'calls', [])
        self.calls.append(name)

    async def authenticate(self, token, key):
        self.record(('authenticate', token, key))

    async def get_capabilities(self):
        self.record('get_capabilities')
        if self.capabilities is not None:
            self.override_capabilities(self.capabilities)
            self._update_capabilities(None)

    async def refresh(self):
        self.record('refresh')
        self._online = self.answers

    async def apply(self):
        self.record('apply')

    async def toggle_display(self):
        self.record('toggle_display')
        self._display_on = not self._display_on


class FakeAC(OfflineMixin, AC):
    capabilities = AC_CAPABILITIES

    def _update_capabilities(self, res):
        # The capabilities are already set by override_capabilities()
        pass


class FakeCC(OfflineMixin, CC):

    def _update_capabilities(self, res):
        pass


def make_config(device_type='AC', **kwargs):
    data = {'eqLogicId': 7, 'deviceId': '42', 'deviceType': device_type, 'ipAddress': '192.0.2.5',
            'protocolVersion': 3, 'token': 'aa' * 64, 'key': 'bb' * 32, 'pollingInterval': 10}
    data.update(kwargs)
    return DeviceConfig.from_jeedom(data)


class DriverTestCase(unittest.IsolatedAsyncioTestCase):
    driver_class = AcDriver
    device_class = FakeAC
    device_type = 'AC'

    async def asyncSetUp(self):
        self.values = {}
        self.events = []

        class Driver(self.driver_class):
            device_class = self.device_class

        self.driver = Driver(make_config(self.device_type), self.publish, self.send_event)
        await self.driver.connect()
        self.assertTrue(await self.driver.refresh_state())
        await self.driver._after_refresh(True)

    def publish(self, eq_logic_id, values):
        self.values.update(values)

    async def send_event(self, event):
        self.events.append(event)


class AcDriverTest(DriverTestCase):

    async def test_connect_and_capabilities(self):
        device = self.driver.device
        self.assertIn(('authenticate', 'aa' * 64, 'bb' * 32), device.calls)
        capabilities = self.events[0]['capabilities']
        self.assertEqual(self.events[0]['action'], 'deviceCapabilities')
        self.assertTrue(capabilities['complete'])
        self.assertEqual((capabilities['minTargetTemperature'], capabilities['maxTargetTemperature']), (17, 30))
        self.assertEqual(capabilities['enums']['mode'], ['auto', 'cool', 'dry', 'heat', 'fan_only'])
        self.assertEqual(capabilities['enums']['preset'], ['none', 'sleep', 'freeze_protection', 'eco', 'turbo'])
        self.assertEqual(capabilities['enums']['breezeMode'], ['off', 'breezeless'])
        for feature in ('swingMode', 'preset', 'breezeMode', 'display', 'customFanSpeed'):
            self.assertIn(feature, capabilities['features'])
        for feature in ('humidity', 'purifier', 'energy', 'cascade'):
            self.assertNotIn(feature, capabilities['features'])
        self.assertEqual(self.values['online'], 1)
        self.assertEqual(self.values['mode'], 'auto')
        self.assertEqual(self.values['preset'], 'none')
        self.assertEqual(self.values['power'], 0)

    async def test_commands(self):
        device = self.driver.device
        await self.driver.execute('setMode', 'cool')
        self.assertEqual((device.operational_mode, device.power_state), (AC.OperationalMode.COOL, True))
        self.assertEqual((self.values['mode'], self.values['power']), ('cool', 1))

        await self.driver.execute('setTargetTemperature', '21,74')
        self.assertEqual(device.target_temperature, 21.5)
        await self.driver.execute('setTargetTemperature', 50)
        self.assertEqual(device.target_temperature, 30)

        await self.driver.execute('setPreset', 'turbo')
        self.assertEqual((device.turbo, device.eco, device.sleep), (True, False, False))
        self.assertEqual(self.values['preset'], 'turbo')

        await self.driver.execute('setFanSpeed', 'low')
        self.assertEqual(self.values['fanSpeed'], 'low')
        await self.driver.execute('setFanSpeedPercent', 55)
        self.assertEqual((self.values['fanSpeed'], self.values['fanSpeedPercent']), ('custom', 55))

        await self.driver.execute('setBreezeMode', 'breezeless')
        self.assertTrue(device.breezeless)
        self.assertEqual(self.values['breezeMode'], 'breezeless')

        await self.driver.execute('toggleDisplay', None)
        self.assertIn('toggle_display', device.calls)

        await self.driver.execute('off', None)
        self.assertEqual(self.values['power'], 0)
        # Beep option and Celsius display are applied with every command
        self.assertTrue(device.sound)
        self.assertFalse(device.fahrenheit)

    async def test_invalid_commands(self):
        for command, value, reason in (
                ('setMode', 'smart_dry', 'unsupportedValue'),
                ('setMode', 'warp', 'invalidValue'),
                ('setPreset', 'ieco', 'unsupportedValue'),
                ('setSwingMode', 'both', 'unsupportedValue'),
                ('setTargetTemperature', 'abc', 'invalidValue'),
                ('launchRocket', None, 'unknownCommand')):
            with self.assertRaises(CommandError) as context:
                await self.driver.execute(command, value)
            self.assertEqual(context.exception.reason, reason, command)

    async def test_only_changes_are_published(self):
        published = []
        self.driver._publish_values = lambda eq_logic_id, values: published.append(values)
        await self.driver._after_refresh(True)
        # online is sent at each successful poll: Jeedom keeps the last communication date
        self.assertEqual(published, [{'online': 1}])
        self.driver.device._indoor_temperature = 23.5
        await self.driver._after_refresh(True)
        self.assertEqual(published[-1], {'online': 1, 'indoorTemperature': 23.5})

    async def test_defrost_command_only_when_reported(self):
        self.assertNotIn('defrost', self.events[-1]['capabilities']['features'])
        self.assertNotIn('defrostActive', self.values)
        self.driver.device._defrost_active = False
        await self.driver._after_refresh(True)
        self.assertIn('defrost', self.events[-1]['capabilities']['features'])
        self.assertEqual(self.values['defrostActive'], 0)
        # Kept when a later answer does not contain it
        self.driver.device._defrost_active = None
        await self.driver._after_refresh(True)
        self.assertIn('defrost', self.events[-1]['capabilities']['features'])

    async def test_diagnostic(self):
        diagnostic = self.driver.diagnostic()
        self.assertEqual(diagnostic['connectionLifetime'], 0)
        self.assertTrue(diagnostic['capabilitiesReceived'])
        self.assertEqual(diagnostic['capabilitiesAnswers'], 1)
        self.assertNotIn('capabilitiesNextTry', diagnostic)
        self.assertNotIn('token', diagnostic['deviceState'])

    async def test_single_failure_is_not_offline(self):
        await self.driver._after_refresh(False)
        self.assertEqual(self.values['online'], 1)
        await self.driver._after_refresh(True)
        await self.driver._after_refresh(False)
        self.assertEqual(self.values['online'], 1)
        await self.driver._after_refresh(False)
        self.assertEqual(self.values['online'], 0)
        self.assertEqual(self.driver.consecutive_failures, 2)

    async def test_offline_and_missing_keys(self):
        self.driver.device.answers = False
        with self.assertRaises(CommandError) as context:
            await self.driver.execute('on', None)
        self.assertEqual(context.exception.reason, 'deviceOffline')
        self.assertFalse(await self.driver.refresh_state())
        await self.driver._after_refresh(False)
        self.assertEqual(self.values['online'], 0)

        class Driver(AcDriver):
            device_class = FakeAC
        driver = Driver(make_config(token='', key=''), self.publish, self.send_event)
        with self.assertRaises(RuntimeError):
            await driver.connect()


class AcDriverLoopTest(unittest.IsolatedAsyncioTestCase):

    @mock.patch('mideamsmart_daemon.drivers.msmart_driver.REFRESH_RETRY_DELAY', 0)
    async def test_polling_loop_offline_after_two_failed_polls(self):
        values = []

        class Driver(AcDriver):
            device_class = FakeAC

        driver = Driver(make_config(), lambda eq_logic_id, v: values.append(v), self._event)
        driver.start()
        await asyncio.sleep(0.05)
        self.assertEqual(values[0], {'online': 1})
        driver.device.answers = False
        driver.request_refresh()
        await asyncio.sleep(0.05)
        self.assertNotIn({'online': 0}, values)
        # Each failed poll was tried twice (new connection)
        self.assertEqual(driver.device.calls.count('refresh'), 3)
        driver.request_refresh()
        await asyncio.sleep(0.05)
        self.assertIn({'online': 0}, values)
        await driver.stop()

    async def _event(self, event):
        pass


class CapabilitiesRetryTest(unittest.IsolatedAsyncioTestCase):

    async def test_capabilities_asked_again_after_a_lost_answer(self):
        events = []

        class SilentAC(FakeAC):
            capabilities = None

        class Driver(AcDriver):
            device_class = SilentAC

        async def send_event(event):
            events.append(event)

        driver = Driver(make_config(connectionLifetime=90), lambda eq_logic_id, values: None, send_event)
        await driver.connect()
        self.assertTrue(await driver.refresh_state())
        await driver._after_refresh(True)
        self.assertFalse(events[-1]['capabilities']['complete'])
        diagnostic = driver.diagnostic()
        self.assertEqual((diagnostic['capabilitiesAnswers'], diagnostic['connectionLifetime']), (0, 90))
        self.assertTrue(0 < diagnostic['capabilitiesNextTry'] <= 30)
        # The appliance answers now: the retry is due after 30 s
        driver.device.capabilities = AC_CAPABILITIES
        with mock.patch('mideamsmart_daemon.drivers.msmart_driver.time.monotonic', return_value=time.monotonic() + 31):
            await driver.refresh_state()
        await driver._after_refresh(True)
        self.assertTrue(events[-1]['capabilities']['complete'])
        self.assertEqual(driver.device.calls.count('get_capabilities'), 2)
        # Forced reload (commands update): asked even when already received
        driver.resend_capabilities()
        await driver.refresh_state()
        self.assertEqual(driver.device.calls.count('get_capabilities'), 3)


class CcDriverTest(DriverTestCase):
    driver_class = CcDriver
    device_class = FakeCC
    device_type = 'CC'

    async def test_defaults_and_commands(self):
        capabilities = self.events[0]['capabilities']
        # No capabilities answer: msmart-ng default capabilities, marked incomplete
        self.assertFalse(capabilities['complete'])
        self.assertIn('fan', capabilities['enums']['mode'])
        self.assertEqual(capabilities['enums']['preset'], ['none', 'eco', 'silent', 'sleep'])
        await self.driver.execute('setPreset', 'silent')
        self.assertEqual(self.values['preset'], 'silent')
        await self.driver.execute('setFanSpeed', 'l3')
        self.assertEqual(self.values['fanSpeed'], 'l3')
        await self.driver.execute('setMode', 'heat')
        self.assertEqual((self.values['mode'], self.values['power']), ('heat', 1))


if __name__ == '__main__':
    unittest.main()

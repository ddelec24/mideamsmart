"""Drivers with the real libraries, against the fake LAN appliances of tools/fake_device.py."""

import asyncio
import socket
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))

from fake_device import FakeAirConditioner, FakeDehumidifier  # noqa: E402

from mideamsmart_daemon.devices import DeviceConfig  # noqa: E402
from mideamsmart_daemon.drivers import DRIVERS, CommandError  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class IntegrationTestCase(unittest.IsolatedAsyncioTestCase):
    fake_class = None
    device_type = ''

    async def asyncSetUp(self):
        self.fake = self.fake_class()
        self.port = free_port()
        self.server = await asyncio.start_server(self.fake.handle, '127.0.0.1', self.port)
        self.values = {}
        self.events = []
        config = DeviceConfig.from_jeedom({'eqLogicId': 3, 'deviceId': '151732605161920', 'deviceType': self.device_type,
                                           'ipAddress': '127.0.0.1', 'port': self.port, 'protocolVersion': 2, 'pollingInterval': 10,
                                           'connectionLifetime': 90})
        self.driver = DRIVERS[self.device_type](config, self.publish, self.send_event)
        self.driver.start()
        await self.wait_for(lambda: self.values.get('online') == 1 and 'mode' in self.values)

    async def asyncTearDown(self):
        await self.driver.stop()
        self.server.close()
        await self.server.wait_closed()

    def publish(self, eq_logic_id, values):
        self.values.update(values)

    async def send_event(self, event):
        self.events.append(event)

    async def wait_for(self, predicate, timeout=15):
        start = time.monotonic()
        while not predicate():
            if time.monotonic() - start > timeout:
                self.fail(f'Timeout, values: {self.values}')
            await asyncio.sleep(0.05)


class AirConditionerIntegrationTest(IntegrationTestCase):
    fake_class = FakeAirConditioner
    device_type = 'AC'

    async def test_state_and_commands(self):
        capabilities = self.events[0]['capabilities']
        self.assertTrue(capabilities['complete'])
        self.assertEqual(capabilities['enums']['fanSpeed'], ['low', 'medium', 'high', 'auto'])
        self.assertEqual((self.values['mode'], self.values['targetTemperature'], self.values['outdoorTemperature']), ('cool', 21.0, 28.5))

        await self.driver.execute('setMode', 'heat')
        await self.driver.execute('setTargetTemperature', 23.5)
        await self.driver.execute('setFanSpeed', 'high')
        self.assertEqual((self.values['mode'], self.values['targetTemperature'], self.values['fanSpeed']), ('heat', 23.5, 'high'))
        await self.driver.execute('off', None)
        self.assertEqual(self.values['power'], 0)

        diagnostic = self.driver.diagnostic()
        self.assertEqual((diagnostic['driver'], diagnostic['online'], diagnostic['consecutiveFailures']), ('AcDriver', True, 0))
        self.assertTrue(diagnostic['capabilitiesReceived'])
        self.assertTrue(diagnostic['library'].startswith('msmart-ng '))
        self.assertNotIn('token', diagnostic['deviceState'])
        self.assertIn('ECO', diagnostic['deviceCapabilities']['additional_capabilities'])


    async def test_appliance_closing_its_connection(self):
        # Remedy of midea-ac-py: reconnection after the configured lifetime
        self.assertEqual(self.driver.device._lan.max_connection_lifetime, 90)
        # The appliance closes the connection without answering one request out of two
        self.fake.drop_every = 2
        for _ in range(4):
            async with self.driver._lock:
                self.assertTrue(await self.driver.refresh_state())
            await self.driver._after_refresh(True)
        self.assertEqual(self.values['online'], 1)
        await self.driver.execute('setMode', 'heat')
        self.assertEqual(self.values['mode'], 'heat')


class DehumidifierIntegrationTest(IntegrationTestCase):
    fake_class = FakeDehumidifier
    device_type = 'A1'

    async def test_state_and_commands(self):
        await self.wait_for(lambda: self.events)
        capabilities = self.events[0]['capabilities']
        self.assertIn('pump', capabilities['features'])
        self.assertIn('continuous', capabilities['enums']['mode'])
        self.assertNotIn('off', capabilities['enums']['fanSpeed'])
        self.assertEqual((self.values['power'], self.values['mode'], self.values['targetHumidity']), (1, 'auto', 50))
        self.assertEqual((self.values['currentHumidity'], self.values['currentTemperature'], self.values['tankLevel']), (62, 20.0, 30))

        await self.driver.execute('off', None)
        await self.wait_for(lambda: self.values['power'] == 0)
        # Choosing a mode turns the dehumidifier on
        await self.driver.execute('setMode', 'continuous')
        await self.wait_for(lambda: self.values['mode'] == 'continuous' and self.values['power'] == 1)
        await self.driver.execute('setTargetHumidity', 90)
        await self.wait_for(lambda: self.values['targetHumidity'] == 85)
        # Commands sent one after the other (schedule slot): the second one keeps the first one
        await self.driver.execute('off', None)
        await self.driver.execute('setMode', 'manual')
        await self.driver.execute('setTargetHumidity', 45)
        await self.wait_for(lambda: self.values['targetHumidity'] == 45)
        self.assertEqual((self.values['power'], self.values['mode']), (1, 'manual'))
        await self.driver.execute('swingOn', None)
        await self.wait_for(lambda: self.values['swing'] == 1)
        await self.driver.execute('setWaterLevelSet', '75')
        await self.wait_for(lambda: self.values['waterLevelSet'] == '75')
        with self.assertRaises(CommandError):
            await self.driver.execute('setFanSpeed', 'turbo')
        diagnostic = self.driver.diagnostic()
        self.assertEqual((diagnostic['driver'], diagnostic['online']), ('A1Driver', True))
        self.assertTrue(diagnostic['library'].startswith('midea-local '))
        self.assertEqual(diagnostic['deviceState']['mode'], 'manual')

    async def test_stop_while_handling_an_update(self):
        # An update waiting for Jeedom (capabilities sending) while the driver stops
        release = asyncio.Event()
        sent = asyncio.Event()

        async def slow_send(event):
            sent.set()
            await release.wait()

        self.driver._capabilities_sent = None
        self.driver._send_event = slow_send
        update = asyncio.ensure_future(self.driver._handle_update({'power': True}))
        await asyncio.wait_for(sent.wait(), 5)
        stop = asyncio.ensure_future(self.driver.stop())
        await asyncio.sleep(0.1)
        self.assertFalse(stop.done())
        release.set()
        await asyncio.wait_for(asyncio.gather(update, stop), 10)
        self.assertIsNone(self.driver.device)

    async def test_offline(self):
        # Stop the driver first: wait_closed() waits for the open connections
        await self.driver.stop()
        self.server.close()
        await self.server.wait_closed()
        self.values.clear()
        self.driver.start()
        await self.wait_for(lambda: self.values.get('online') == 0, timeout=30)
        self.assertIsNotNone(self.driver.offline_since)
        with self.assertRaises(CommandError) as context:
            await self.driver.execute('on', None)
        self.assertEqual(context.exception.reason, 'deviceOffline')


if __name__ == '__main__':
    unittest.main()

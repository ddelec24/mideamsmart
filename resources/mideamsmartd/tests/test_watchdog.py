import unittest

from mideamsmart_daemon.devices import DeviceConfig
from mideamsmart_daemon.discovery import LanDevice
from mideamsmart_daemon.watchdog import OFFLINE_DELAY, SEARCH_INTERVAL, AddressWatchdog


class FakeClock:
    def __init__(self) -> None:
        self.now = 10000.0

    def __call__(self) -> float:
        return self.now


class FakeDriver:
    def __init__(self, eq_logic_id, device_id, ip_address, offline_since=None) -> None:
        self.config = DeviceConfig.from_jeedom({'eqLogicId': eq_logic_id, 'deviceId': str(device_id), 'deviceType': 'AC',
                                                'ipAddress': ip_address})
        self.offline_since = offline_since


class FakeManager:
    def __init__(self, drivers) -> None:
        self.drivers = {driver.config.eq_logic_id: driver for driver in drivers}
        self.broadcast_addresses = ('192.168.1.255',)


class AddressWatchdogTest(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.clock = FakeClock()
        self.events = []
        self.searches = []
        self.lan = {
            101: LanDevice(101, 0xAC, '192.168.1.50', 6444, 3, '', ''),
            102: LanDevice(102, 0xAC, '192.168.1.11', 6444, 3, '', ''),
        }

    async def discover(self, addresses):
        self.searches.append(addresses)
        return self.lan

    async def send(self, event):
        self.events.append(event)

    def watchdog(self, drivers):
        return AddressWatchdog(FakeManager(drivers), self.send, discover_fn=self.discover, clock=self.clock)

    async def test_new_address_reported(self):
        moved = FakeDriver(1, 101, '192.168.1.10', offline_since=self.clock.now - OFFLINE_DELAY)
        same = FakeDriver(2, 102, '192.168.1.11', offline_since=self.clock.now - OFFLINE_DELAY)
        online = FakeDriver(3, 103, '192.168.1.12')
        await self.watchdog([moved, same, online]).check()
        self.assertEqual(self.searches, [['192.168.1.255']])
        self.assertEqual(self.events, [{'action': 'deviceAddressChanged', 'eqLogicId': 1, 'ipAddress': '192.168.1.50', 'port': 6444}])

    async def test_no_search_too_early_or_too_often(self):
        recent = FakeDriver(1, 101, '192.168.1.10', offline_since=self.clock.now - 10)
        watchdog = self.watchdog([recent])
        await watchdog.check()
        self.assertEqual(self.searches, [])

        recent.offline_since = self.clock.now - OFFLINE_DELAY
        await watchdog.check()
        await watchdog.check()
        self.assertEqual(len(self.searches), 1)
        self.clock.now += SEARCH_INTERVAL
        await watchdog.check()
        self.assertEqual(len(self.searches), 2)


if __name__ == '__main__':
    unittest.main()

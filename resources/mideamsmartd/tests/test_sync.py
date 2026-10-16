import unittest

from mideamsmart_daemon.cloud import CloudAppliance, CloudError
from mideamsmart_daemon.discovery import KeyCheckResult, LanDevice
from mideamsmart_daemon.sync import SyncRequest, SyncService

AC_V3 = 1001
AC_V2 = 1002
A1_SHARED = 1003
FAN = 1004
LAN_ONLY = 1005
CLOUD_ONLY = 1006

LAN_DEVICES = {
    AC_V3: LanDevice(AC_V3, 0xAC, '192.168.1.10', 6444, 3, 'SN-LAN', 'LANMODEL'),
    AC_V2: LanDevice(AC_V2, 0xAC, '192.168.1.11', 6444, 2, '', ''),
    A1_SHARED: LanDevice(A1_SHARED, 0xA1, '192.168.1.12', 6444, 3, '', ''),
    FAN: LanDevice(FAN, 0xFA, '192.168.1.13', 6444, 3, '', ''),
    LAN_ONLY: LanDevice(LAN_ONLY, 0xAC, '192.168.1.14', 6444, 3, '', ''),
}
CLOUD_APPLIANCES = [
    CloudAppliance(AC_V3, 'Salon', 0xAC, 'SN-CLOUD', 'Q1F', True),
    CloudAppliance(AC_V2, 'Chambre', 0xAC, '', '', True),
    CloudAppliance(A1_SHARED, 'Cave', 0xA1, '', '', True),
    CloudAppliance(FAN, 'Ventilateur', 0xFA, '', '', True),
    CloudAppliance(CLOUD_ONLY, 'Bureau', 0xAC, '', '', False),
]


class FakeCloudSession:
    login_error: CloudError | None = None
    key_requests: list[int] = []

    def __init__(self, account, password, guard) -> None:
        pass

    async def __aenter__(self):
        if FakeCloudSession.login_error:
            raise FakeCloudSession.login_error
        return self

    async def __aexit__(self, *exc_info):
        pass

    async def list_appliances(self):
        return CLOUD_APPLIANCES

    async def get_key_candidates(self, appliance_id):
        FakeCloudSession.key_requests.append(appliance_id)
        if appliance_id == A1_SHARED:
            raise CloudError('notOwned', 3201)
        return [('bad-token', 'bad-key'), ('good-token', 'good-key')]


class SyncServiceTest(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        FakeCloudSession.login_error = None
        FakeCloudSession.key_requests = []
        self.discover_calls = []
        self.steps = []

    async def fake_discover(self, addresses):
        self.discover_calls.append(addresses)
        return dict(LAN_DEVICES)

    async def fake_check_keys(self, ip, port, device_id, candidates):
        for pair in candidates:
            if pair[0] == 'good-token':
                return KeyCheckResult.VALID, pair
        return KeyCheckResult.INVALID, None

    async def progress(self, step):
        self.steps.append(step)

    async def sync(self, message):
        service = SyncService(None, discover_fn=self.fake_discover, check_keys_fn=self.fake_check_keys,
                              cloud_session_factory=FakeCloudSession)
        result = await service.run(SyncRequest.from_jeedom(message), self.progress)
        return result, {int(d['deviceId']): d for d in result['devices']}

    async def test_full_sync(self):
        result, devices = await self.sync({'account': 'user@example.com', 'password': 'x', 'broadcastAddress': '192.168.1.255, 10.0.0.255',
                                          'knownDevices': {}})
        self.assertIsNone(result['cloudError'])
        self.assertEqual(self.steps, ['discovery', 'cloudLogin', 'cloudDevices', 'keys'])
        self.assertEqual(self.discover_calls, [['192.168.1.255', '10.0.0.255']])

        salon = devices[AC_V3]
        self.assertEqual((salon['name'], salon['deviceType'], salon['ipAddress'], salon['protocolVersion']), ('Salon', 'AC', '192.168.1.10', 3))
        self.assertEqual((salon['keysStatus'], salon['token'], salon['key']), ('valid', 'good-token', 'good-key'))
        self.assertEqual(salon['serialNumber'], 'SN-CLOUD')
        self.assertEqual(devices[AC_V2]['keysStatus'], 'notNeeded')
        self.assertEqual(devices[A1_SHARED]['keysStatus'], 'notOwned')
        self.assertEqual((devices[FAN]['supported'], devices[FAN]['keysStatus'], devices[FAN]['deviceType']), (False, 'unsupported', 'FA'))
        self.assertEqual(devices[LAN_ONLY]['keysStatus'], 'notInCloud')
        self.assertEqual((devices[CLOUD_ONLY]['keysStatus'], devices[CLOUD_ONLY]['onLan']), ('notOnLan', False))
        # No cloud key request for appliances that do not need it
        self.assertEqual(sorted(FakeCloudSession.key_requests), [AC_V3, A1_SHARED])

    async def test_known_keys_are_not_requested_again(self):
        _, devices = await self.sync({'account': 'user@example.com', 'password': 'x',
                                     'knownDevices': {str(AC_V3): {'hasKeys': True, 'ipAddress': '192.168.1.10'}}})
        self.assertEqual(devices[AC_V3]['keysStatus'], 'known')
        self.assertEqual(devices[AC_V3]['token'], '')
        self.assertNotIn(AC_V3, FakeCloudSession.key_requests)

    async def test_without_account(self):
        result, devices = await self.sync({'broadcastAddress': ''})
        self.assertIsNone(result['cloudError'])
        self.assertEqual(self.steps, ['discovery'])
        self.assertEqual(self.discover_calls, [[]])
        self.assertEqual(devices[AC_V3]['keysStatus'], 'noAccount')
        self.assertEqual(devices[AC_V2]['keysStatus'], 'notNeeded')
        self.assertNotIn(CLOUD_ONLY, devices)

    async def test_cloud_error_keeps_lan_devices(self):
        FakeCloudSession.login_error = CloudError('accountLocked', 7610, 900)
        result, devices = await self.sync({'account': 'user@example.com', 'password': 'x'})
        self.assertEqual(result['cloudError'], {'reason': 'accountLocked', 'cloudCode': 7610, 'retryAfter': 900})
        self.assertEqual(devices[AC_V3]['keysStatus'], 'cloudError')
        self.assertEqual(len(devices), len(LAN_DEVICES))

    async def test_single_device_keys(self):
        result, devices = await self.sync({'account': 'user@example.com', 'password': 'x', 'onlyDeviceId': str(AC_V3), 'forceKeys': True,
                                          'knownDevices': {str(AC_V3): {'hasKeys': True, 'ipAddress': '192.168.1.10', 'port': 6444}}})
        self.assertEqual(result['onlyDeviceId'], str(AC_V3))
        self.assertEqual(self.discover_calls, [['192.168.1.10']])
        self.assertEqual(list(devices), [AC_V3])
        self.assertEqual(devices[AC_V3]['keysStatus'], 'valid')


if __name__ == '__main__':
    unittest.main()

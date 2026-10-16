import unittest
from unittest import mock

from midealocal.exceptions import CloudLoginError, NoDeviceRegistered

from mideamsmart_daemon.cloud import CloudError, CloudGuard, CloudSession


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class CloudGuardTest(unittest.TestCase):

    def setUp(self) -> None:
        self.clock = FakeClock()
        self.guard = CloudGuard(clock=self.clock)

    def assert_refused(self, reason: str) -> CloudError:
        with self.assertRaises(CloudError) as context:
            self.guard.check('user@example.com', 'secret')
        self.assertEqual(context.exception.reason, reason)
        return context.exception

    def test_min_interval_between_logins(self):
        self.guard.check('user@example.com', 'secret')
        self.guard.record_attempt()
        self.clock.now += 10
        self.assertEqual(self.assert_refused('tooFrequent').retry_after, 21)
        self.clock.now += 25
        self.guard.check('user@example.com', 'secret')

    def test_lockout_after_too_many_failures(self):
        self.guard.record_attempt()
        self.guard.record_error(7610, 'user@example.com', 'secret')
        self.clock.now += 60
        error = self.assert_refused('accountLocked')
        self.assertEqual(error.cloud_code, 7610)
        self.clock.now += 15 * 60
        self.guard.check('user@example.com', 'secret')

    def test_rejected_credentials_until_changed(self):
        self.guard.record_error(3102, 'user@example.com', 'secret')
        self.clock.now += 3600
        self.assert_refused('invalidCredentials')
        self.guard.check('user@example.com', 'new-secret')


class FakeMideaCloud:
    def __init__(self, login_error=None, keys=None, keys_error=None) -> None:
        self.login_error = login_error
        self.keys = keys or {}
        self.keys_error = keys_error

    async def login(self) -> bool:
        if self.login_error:
            raise self.login_error
        return True

    async def list_appliances(self, home_id):
        return {
            15393162840672: {'name': 'Salon', 'type': 0xAC, 'sn': 'SN1', 'sn8': '00000Q1F', 'online': True},
            15393162840673: {'name': 'Cave', 'type': 0xA1, 'sn': 'SN2', 'sn8': '', 'model': 'X', 'online': False},
        }

    async def get_cloud_keys(self, appliance_id):
        if self.keys_error:
            raise self.keys_error
        return self.keys


class CloudSessionTest(unittest.IsolatedAsyncioTestCase):

    def session(self, fake_cloud, guard=None) -> CloudSession:
        patcher = mock.patch('mideamsmart_daemon.cloud.get_midea_cloud', return_value=fake_cloud)
        patcher.start()
        self.addCleanup(patcher.stop)
        return CloudSession('user@example.com', 'secret', guard or CloudGuard())

    async def test_list_and_keys(self):
        fake = FakeMideaCloud(keys={2: {'token': 'T2', 'key': 'K2'}, 1: {'token': 'T1', 'key': 'K1'}})
        async with self.session(fake) as cloud:
            appliances = await cloud.list_appliances()
            self.assertEqual([a.appliance_id for a in appliances], [15393162840672, 15393162840673])
            self.assertEqual(appliances[0].model, '00000Q1F')
            self.assertEqual(appliances[1].device_type, 0xA1)
            self.assertEqual(await cloud.get_key_candidates(15393162840672), [('T1', 'K1'), ('T2', 'K2')])

    async def test_login_lockout_is_remembered(self):
        guard = CloudGuard()
        with self.assertRaises(CloudError) as context:
            async with self.session(FakeMideaCloud(login_error=CloudLoginError(7610, 'locked')), guard):
                pass
        self.assertEqual(context.exception.reason, 'accountLocked')
        self.assertEqual(context.exception.to_jeedom()['cloudCode'], 7610)
        with self.assertRaises(CloudError) as context:
            guard.check('user@example.com', 'secret')
        self.assertEqual(context.exception.reason, 'accountLocked')

    async def test_not_owned_appliance(self):
        fake = FakeMideaCloud(keys_error=NoDeviceRegistered(3201, 'not yours'))
        async with self.session(fake) as cloud:
            with self.assertRaises(CloudError) as context:
                await cloud.get_key_candidates(1)
        self.assertEqual(context.exception.reason, 'notOwned')


if __name__ == '__main__':
    unittest.main()

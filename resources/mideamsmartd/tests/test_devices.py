import unittest

from mideamsmart_daemon.devices import DeviceConfig, DeviceConfigError, DeviceManager

JEEDOM_DEVICE = {
    'eqLogicId': 12,
    'deviceId': '15393162840672',
    'deviceType': 'ac',
    'name': '[Salon][Clim]',
    'ipAddress': ' 192.168.1.20 ',
    'port': 6444,
    'protocolVersion': 3,
    'token': 'aa' * 64,
    'key': 'bb' * 32,
    'pollingInterval': 30,
}


class DeviceConfigTest(unittest.TestCase):

    def test_from_jeedom(self):
        config = DeviceConfig.from_jeedom(JEEDOM_DEVICE)
        self.assertEqual(config.eq_logic_id, 12)
        self.assertEqual(config.device_id, 15393162840672)
        self.assertEqual(config.device_type, 'AC')
        self.assertEqual(config.ip_address, '192.168.1.20')
        self.assertEqual(config.polling_interval, 30)

    def test_defaults_and_minimum_polling(self):
        config = DeviceConfig.from_jeedom({'eqLogicId': '3', 'deviceId': '', 'port': '', 'pollingInterval': 2})
        self.assertEqual(config.device_id, 0)
        self.assertEqual(config.port, 6444)
        self.assertEqual(config.protocol_version, 3)
        self.assertEqual(config.polling_interval, 10)

    def test_invalid_values(self):
        with self.assertRaises(DeviceConfigError):
            DeviceConfig.from_jeedom({'deviceId': '1'})
        with self.assertRaises(DeviceConfigError):
            DeviceConfig.from_jeedom({'eqLogicId': 1, 'deviceId': 'abc'})
        with self.assertRaises(DeviceConfigError):
            DeviceConfig.from_jeedom({'eqLogicId': 1, 'port': 'x'})

    def test_secrets_not_in_repr(self):
        # The dataclass repr is used in logs: secrets must not appear
        self.assertNotIn('aaaa', repr(DeviceConfig.from_jeedom(JEEDOM_DEVICE)))


class DeviceManagerTest(unittest.TestCase):

    def test_set_update_remove(self):
        manager = DeviceManager()
        manager.set_devices([JEEDOM_DEVICE, dict(JEEDOM_DEVICE, eqLogicId=13), {'invalid': True}])
        self.assertEqual(sorted(manager.devices), [12, 13])

        manager.update_device(dict(JEEDOM_DEVICE, ipAddress='192.168.1.21'))
        self.assertEqual(manager.devices[12].ip_address, '192.168.1.21')

        manager.remove_device('13')
        self.assertEqual(sorted(manager.devices), [12])

        manager.set_devices([dict(JEEDOM_DEVICE, eqLogicId=14)])
        self.assertEqual(sorted(manager.devices), [14])


if __name__ == '__main__':
    unittest.main()

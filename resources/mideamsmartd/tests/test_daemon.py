"""End-to-end tests of the daemon against a fake Jeedom callback."""

import asyncio
import json
import os
import socket
import tempfile
import unittest

from aiohttp import web

from mideamsmart_daemon.daemon import Daemon
from mideamsmart_daemon.jeedom import JeedomSocketServer, merge_dict, redact

APIKEY = 'test-apikey'


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class FakeJeedom:
    """Plays the role of core/php/jeemideamsmart.php."""

    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.received = asyncio.Condition()
        self.runner: web.AppRunner | None = None
        self.port = free_port()

    @property
    def url(self) -> str:
        return f'http://127.0.0.1:{self.port}/plugins/mideamsmart/core/php/jeemideamsmart.php'

    async def start(self) -> None:
        app = web.Application()
        app.router.add_route('*', '/plugins/mideamsmart/core/php/jeemideamsmart.php', self.handle)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        await web.TCPSite(self.runner, '127.0.0.1', self.port).start()

    async def stop(self) -> None:
        await self.runner.cleanup()

    async def handle(self, request: web.Request) -> web.Response:
        if request.query.get('apikey') != APIKEY:
            return web.Response(text='unauthorized')
        if request.query.get('test'):
            return web.Response(text='OK')
        message = await request.json()
        async with self.received:
            self.messages.append(message)
            self.received.notify_all()
        return web.Response(text='')

    async def wait_for(self, action: str, timeout: float = 5) -> dict:
        async with self.received:
            await asyncio.wait_for(self.received.wait_for(
                lambda: any(m.get('action') == action for m in self.messages)), timeout)
        return next(m for m in self.messages if m.get('action') == action)


async def send_to_daemon(port: int, message: dict) -> None:
    """Same protocol as mideamsmart::sendToDaemon()."""
    _, writer = await asyncio.open_connection('127.0.0.1', port)
    writer.write((json.dumps(message) + '\n').encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def wait_until(predicate, timeout: float = 5) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.05)


class HelpersTest(unittest.TestCase):

    def test_redact(self):
        message = {'action': 'setDevices', 'apikey': 'secret', 'devices': [{'token': 'abc', 'key': '', 'ipAddress': '1.2.3.4'}]}
        self.assertEqual(redact(message), {'action': 'setDevices', 'apikey': '***', 'devices': [{'token': '***', 'key': '', 'ipAddress': '1.2.3.4'}]})
        self.assertEqual(message['apikey'], 'secret')

    def test_merge_dict(self):
        target = {'12': {'power': 1, 'mode': 'cool'}}
        merge_dict(target, {'12': {'mode': 'heat'}, '13': {'power': 0}})
        self.assertEqual(target, {'12': {'power': 1, 'mode': 'heat'}, '13': {'power': 0}})

    def test_parse_message(self):
        server = JeedomSocketServer('127.0.0.1', 0, APIKEY, None)
        self.assertEqual(server.parse_message(b'{"apikey": "test-apikey", "action": "x"}\n'), {'action': 'x'})
        self.assertIsNone(server.parse_message(b'{"apikey": "wrong", "action": "x"}\n'))
        self.assertIsNone(server.parse_message(b'{"action": "x"}\n'))
        self.assertIsNone(server.parse_message(b'not json\n'))
        self.assertIsNone(server.parse_message(b'[1, 2]\n'))


class DaemonTest(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.jeedom = FakeJeedom()
        await self.jeedom.start()
        self.tmp = tempfile.TemporaryDirectory()
        self.pid_file = os.path.join(self.tmp.name, 'mideamsmart', 'deamon.pid')
        self.socket_port = free_port()

    async def asyncTearDown(self) -> None:
        await self.jeedom.stop()
        self.tmp.cleanup()

    def make_daemon(self, callback_url: str | None = None) -> Daemon:
        return Daemon(socket_host='127.0.0.1', socket_port=self.socket_port, callback_url=callback_url or self.jeedom.url,
                      apikey=APIKEY, pid_file=self.pid_file, cycle=0.1)

    async def test_life_cycle(self):
        daemon = self.make_daemon()
        run_task = asyncio.create_task(daemon.run())

        started = await self.jeedom.wait_for('daemonStarted')
        self.assertEqual(started['pid'], os.getpid())
        with open(self.pid_file, encoding='ascii') as pid_file:
            self.assertEqual(pid_file.read(), str(os.getpid()))

        # Jeedom answers daemonStarted with the list of equipments
        devices = [{'eqLogicId': 12, 'deviceId': '1', 'deviceType': 'AC'}, {'eqLogicId': 13, 'deviceId': '2', 'deviceType': 'A1'}]
        await send_to_daemon(self.socket_port, {'apikey': APIKEY, 'action': 'setDevices', 'devices': devices})
        await wait_until(lambda: sorted(daemon.device_manager.devices) == [12, 13])

        # A message with a wrong apikey is ignored
        await send_to_daemon(self.socket_port, {'apikey': 'wrong', 'action': 'removeDevice', 'eqLogicId': 12})
        await send_to_daemon(self.socket_port, {'apikey': APIKEY, 'action': 'updateDevice', 'device': {'eqLogicId': 14, 'deviceId': '3'}})
        await wait_until(lambda: 14 in daemon.device_manager.devices)
        self.assertIn(12, daemon.device_manager.devices)

        await send_to_daemon(self.socket_port, {'apikey': APIKEY, 'action': 'removeDevice', 'eqLogicId': 12})
        await wait_until(lambda: 12 not in daemon.device_manager.devices)

        # Values are merged then sent together
        daemon._callback.add_values(13, {'power': 1})
        daemon._callback.add_values(13, {'targetHumidity': 50})
        values = await self.jeedom.wait_for('deviceValues')
        self.assertEqual(values['devices'], {'13': {'power': 1, 'targetHumidity': 50}})

        await send_to_daemon(self.socket_port, {'apikey': APIKEY, 'action': 'stop'})
        self.assertEqual(await asyncio.wait_for(run_task, 5), 0)
        self.assertFalse(os.path.exists(self.pid_file))
        # The socket is closed
        with self.assertRaises(OSError):
            await send_to_daemon(self.socket_port, {'apikey': APIKEY, 'action': 'stop'})

    async def test_unreachable_jeedom(self):
        daemon = self.make_daemon(callback_url=f'http://127.0.0.1:{free_port()}/jeemideamsmart.php')
        self.assertEqual(await asyncio.wait_for(daemon.run(), 10), 1)
        self.assertFalse(os.path.exists(self.pid_file))

    async def test_port_already_used(self):
        with socket.socket() as busy:
            busy.bind(('127.0.0.1', self.socket_port))
            busy.listen()
            daemon = self.make_daemon()
            self.assertEqual(await asyncio.wait_for(daemon.run(), 10), 1)
        self.assertFalse(os.path.exists(self.pid_file))


if __name__ == '__main__':
    unittest.main()

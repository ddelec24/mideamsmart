"""Fake Midea appliances (LAN protocol V2), to test the plugin without an appliance.

Usage (with the plugin venv, which contains msmart-ng):
  resources/python_venv/bin/python3 tools/fake_device.py --type ac|a1 [--host 127.0.0.1] [--port 6444] [--drop-every N]

Then set an equipment of the same type to this IP and port, protocol V2. The received
commands are printed.

- ac: air conditioner. Answers the capabilities and state requests with frames captured from
  real appliances (msmart-ng tests) and keeps the power, mode, target temperature and fan
  speed sent by the SetState commands.
- a1: dehumidifier. Answers the queries with a state built from the layout of the
  midea-local responses and applies the Set commands.
"""

import argparse
import asyncio

from msmart.lan import _Packet  # pylint: disable=protected-access

# Frames captured from real appliances (msmart-ng test suite)
CAPABILITIES_FRAME = bytes.fromhex(
    'aa29ac00000000000303b5071202010113020101140201011502010116020101170201001a020101dedb')
STATE_FRAME = bytes.fromhex(
    'aa23ac00000000000303c00145660000003c0010045c6b20000000000000000000020d79')

COMMAND_CAPABILITIES = 0xB5
COMMAND_GET_STATE = 0x41
COMMAND_SET_STATE = 0x40


def checksum(frame: bytes) -> int:
    return (~sum(frame) + 1) & 0xFF


def crc8(data: bytes) -> int:
    # Same CRC-8 (Dallas/Maxim) as msmart.crc8
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8C if crc & 1 else crc >> 1
    return crc


class FakeDevice:
    """LAN server: decodes the packets and sends the frame returned by answer()."""

    # Closes the connection without answering one request out of drop_every (0 = never), like
    # the appliances that close their connection by themselves
    drop_every = 0
    _requests = 0

    def answer(self, frame: bytes) -> bytes | None:
        raise NotImplementedError

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info('peername')
        print(f'Connection from {peer}', flush=True)
        try:
            while True:
                header = await reader.readexactly(6)
                length = int.from_bytes(header[4:6], 'little')
                packet = header + await reader.readexactly(length - 6)
                device_id = int.from_bytes(packet[20:28], 'little')
                try:
                    frame = _Packet.decode(packet)
                except ValueError:
                    continue  # heartbeat, without payload
                if not frame or frame[0] != 0xAA:
                    continue
                print(f'Received message type 0x{frame[9]:02X} body 0x{frame[10]:02X}: {frame.hex()}', flush=True)
                self._requests += 1
                if self.drop_every and self._requests % self.drop_every == 0:
                    print(f'Closing the connection of {peer} without answering', flush=True)
                    break
                response = self.answer(frame)
                if response is not None:
                    writer.write(_Packet.encode(device_id, response))
                    await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            print(f'Connection closed by {peer}', flush=True)
        finally:
            writer.close()


class FakeAirConditioner(FakeDevice):

    def __init__(self) -> None:
        self.state = bytearray(STATE_FRAME)

    def apply_set_state(self, frame: bytes) -> None:
        """Copies power, mode, target temperature and fan speed from a SetState frame."""
        payload = frame[10:]
        state_payload = self.state[10:-1]
        # SetState byte 1: power (bit 0) | mode (bits 5-7) | target temperature (bits 0-3) + 16
        state_payload[1] = (state_payload[1] & 0xFE) | (payload[1] & 0x01)
        state_payload[2] = payload[2]
        state_payload[3] = payload[3]
        state_payload[-1] = crc8(bytes(state_payload[:-1]))
        self.state[10:-1] = state_payload
        self.state[-1] = checksum(bytes(self.state[1:-1]))

    def answer(self, frame: bytes) -> bytes | None:
        command = frame[10] if len(frame) > 10 else None
        if command == COMMAND_CAPABILITIES:
            return CAPABILITIES_FRAME
        if command == COMMAND_SET_STATE:
            self.apply_set_state(frame)
            return bytes(self.state)
        if command == COMMAND_GET_STATE:
            return bytes(self.state)
        return None


class FakeDehumidifier(FakeDevice):
    MESSAGE_SET = 0x02
    MESSAGE_QUERY = 0x03
    MESSAGE_APPLIANCE = 0xA0

    def __init__(self) -> None:
        body = bytearray(21)
        body[0] = 0xC8
        body[1] = 0x01  # power on
        body[2] = 3  # auto
        body[3] = 60  # medium
        body[7] = 50  # target humidity
        body[9] = 0x10  # pump available, off
        body[10] = 30  # tank level
        body[15] = 50  # water level threshold
        body[16] = 62  # current humidity
        body[17] = 20 * 2 + 50  # current temperature 20 °C
        self.body = body

    def frame(self, message_type: int) -> bytes:
        frame = bytearray([0xAA, 10 + len(self.body), 0xA1, 0, 0, 0, 0, 0, 0, message_type]) + self.body
        frame.append(checksum(bytes(frame[1:])))
        return bytes(frame)

    def apply_set(self, payload: bytes) -> None:
        body = self.body
        body[1] = payload[1] & 0x01
        body[2] = payload[2]
        body[3] = payload[3]
        body[7] = payload[7]
        body[8] = payload[8] & 0x80
        filter_reset = payload[9] & 0x80
        body[9] = payload[9] & 0x58 | (0 if filter_reset else body[9] & 0x80)
        body[19] = 0x20 if payload[10] & 0x08 else 0
        body[15] = payload[13]

    def appliance_frame(self) -> bytes:
        # Answer to the appliance query (protocol detection): header only, empty body
        frame = bytearray([0xAA, 10 + 20, 0xA1, 0, 0, 0, 0, 0, 0, self.MESSAGE_APPLIANCE]) + bytearray(20)
        frame.append(checksum(bytes(frame[1:])))
        return bytes(frame)

    def answer(self, frame: bytes) -> bytes | None:
        message_type = frame[9]
        if message_type == self.MESSAGE_APPLIANCE:
            return self.appliance_frame()
        if message_type == self.MESSAGE_QUERY and frame[10] == 0x41:
            return self.frame(self.MESSAGE_QUERY)
        if message_type == self.MESSAGE_SET and frame[10] == 0x48:
            self.apply_set(frame[10:])
            return self.frame(self.MESSAGE_SET)
        return None


DEVICES = {'ac': FakeAirConditioner, 'a1': FakeDehumidifier}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--type', choices=sorted(DEVICES), default='ac')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=6444)
    parser.add_argument('--drop-every', type=int, default=0, help='close the connection without answering one request out of N')
    args = parser.parse_args()
    device = DEVICES[args.type]()
    device.drop_every = args.drop_every
    server = await asyncio.start_server(device.handle, args.host, args.port)
    print(f'Fake {args.type} listening on {args.host}:{args.port}', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())

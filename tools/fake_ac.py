"""Fake Midea air conditioner (LAN protocol V2), to test the plugin without an appliance.

Usage (with the plugin venv, which contains msmart-ng):
  resources/python_venv/bin/python3 tools/fake_ac.py [--host 127.0.0.1] [--port 6444]

Then set an AC equipment to this IP and port, protocol V2. The appliance answers the
capabilities and state requests with frames captured from real appliances (msmart-ng tests),
and keeps the power, mode, target temperature and fan speed sent by the SetState commands.
The received commands are printed.
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


class FakeAirConditioner:

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

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info('peername')
        print(f'Connection from {peer}', flush=True)
        try:
            while True:
                header = await reader.readexactly(6)
                length = int.from_bytes(header[4:6], 'little')
                packet = header + await reader.readexactly(length - 6)
                device_id = int.from_bytes(packet[20:28], 'little')
                frame = _Packet.decode(packet)
                print(f'Received command 0x{frame[10]:02X}: {frame.hex()}', flush=True)
                response = self.answer(frame)
                if response is not None:
                    writer.write(_Packet.encode(device_id, response))
                    await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            print(f'Connection closed by {peer}', flush=True)
        finally:
            writer.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=6444)
    args = parser.parse_args()
    device = FakeAirConditioner()
    server = await asyncio.start_server(device.handle, args.host, args.port)
    print(f'Fake air conditioner listening on {args.host}:{args.port}', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())

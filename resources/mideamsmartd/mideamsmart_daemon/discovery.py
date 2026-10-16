"""Discovery of the appliances on the local network and check of their keys."""

import asyncio
import logging
from dataclasses import dataclass

from midealocal import discover as midea_discover
from msmart.lan import LAN, AuthenticationError, ProtocolError

_LOGGER = logging.getLogger(__name__)

KEY_CHECK_TIMEOUT = 20


@dataclass(frozen=True)
class LanDevice:
    device_id: int
    device_type: int
    ip_address: str
    port: int
    protocol_version: int
    serial_number: str
    model: str


def _discover_sync(broadcast_address: str | None) -> dict[int, dict]:
    # midealocal takes a single address (or None to scan every private interface)
    return midea_discover.discover(ip_address=broadcast_address)


async def discover(broadcast_addresses: list[str]) -> dict[int, LanDevice]:
    """Broadcast discovery, on every given address (all private interfaces when empty)."""
    targets: list[str | None] = list(broadcast_addresses) or [None]
    _LOGGER.info('Searching appliances on the local network (%s)', ', '.join(t or 'all interfaces' for t in targets))
    results = await asyncio.gather(*(asyncio.to_thread(_discover_sync, target) for target in targets), return_exceptions=True)
    devices: dict[int, LanDevice] = {}
    for target, result in zip(targets, results):
        if isinstance(result, BaseException):
            _LOGGER.warning('Discovery failed on %s: %s', target or 'all interfaces', result)
            continue
        for device_id, info in result.items():
            devices[int(device_id)] = LanDevice(
                device_id=int(device_id),
                device_type=int(info.get('type') or 0),
                ip_address=str(info.get('ip_address') or ''),
                port=int(info.get('port') or 6444),
                protocol_version=int(info.get('protocol') or 3),
                serial_number=str(info.get('sn') or ''),
                model=str(info.get('model') or ''),
            )
    _LOGGER.info('%s appliance(s) found on the local network', len(devices))
    return devices


class KeyCheckResult:
    VALID = 'valid'
    INVALID = 'invalid'
    UNREACHABLE = 'unreachable'


async def check_keys(ip_address: str, port: int, device_id: int,
                     candidates: list[tuple[str, str]]) -> tuple[str, tuple[str, str] | None]:
    """Tries the token/key pairs with a V3 handshake: (KeyCheckResult, accepted pair or None)."""
    for token, key in candidates:
        lan = LAN(ip_address, port, device_id)
        try:
            await asyncio.wait_for(lan.authenticate(token, key), KEY_CHECK_TIMEOUT)
            _LOGGER.info('Keys accepted by the appliance %s', device_id)
            return KeyCheckResult.VALID, (token, key)
        except AuthenticationError:
            _LOGGER.debug('Keys refused by the appliance %s, trying the next ones', device_id)
        except (ProtocolError, TimeoutError, OSError) as error:
            _LOGGER.warning('Unable to check the keys of the appliance %s (%s:%s): %s', device_id, ip_address, port, error)
            return KeyCheckResult.UNREACHABLE, None
        finally:
            # LAN has no public close: drop the connection opened for the check
            lan._disconnect()  # pylint: disable=protected-access
    return KeyCheckResult.INVALID, None

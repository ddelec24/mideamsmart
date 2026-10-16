"""Synchronization: appliances of the MSmartHome account + local discovery + keys."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .cloud import CloudAppliance, CloudError, CloudGuard, CloudSession
from .discovery import KeyCheckResult, LanDevice, check_keys, discover

_LOGGER = logging.getLogger(__name__)

SUPPORTED_DEVICE_TYPES = {0xAC: 'AC', 0xCC: 'CC', 0xA1: 'A1'}


class KeysStatus:
    NOT_NEEDED = 'notNeeded'  # V2 appliance, no key
    KNOWN = 'known'  # already set in Jeedom, not asked again
    VALID = KeyCheckResult.VALID  # retrieved from the cloud and accepted by the appliance
    INVALID = KeyCheckResult.INVALID  # retrieved from the cloud but refused by the appliance
    UNREACHABLE = KeyCheckResult.UNREACHABLE  # the appliance did not answer the check
    NOT_OWNED = 'notOwned'  # appliance shared with the account, not paired with it
    NOT_IN_CLOUD = 'notInCloud'  # found on the LAN but not in the account
    NOT_ON_LAN = 'notOnLan'  # in the account but not found on the LAN
    NO_ACCOUNT = 'noAccount'  # no MSmartHome account configured
    CLOUD_ERROR = 'cloudError'  # the cloud did not answer
    UNSUPPORTED = 'unsupported'  # appliance type not handled by the plugin


def device_type_code(device_type: int) -> str:
    return f'{device_type:02X}'


@dataclass(frozen=True)
class KnownDevice:
    has_keys: bool
    ip_address: str = ''
    port: int = 6444


@dataclass(frozen=True)
class SyncRequest:
    account: str = ''
    password: str = field(default='', repr=False)
    broadcast_addresses: tuple[str, ...] = ()
    known_devices: dict[int, KnownDevice] = field(default_factory=dict)
    only_device_id: int | None = None
    force_keys: bool = False

    @classmethod
    def from_jeedom(cls, message: dict[str, Any]) -> 'SyncRequest':
        known = {}
        for device_id, info in (message.get('knownDevices') or {}).items():
            try:
                known[int(device_id)] = KnownDevice(
                    has_keys=bool(info.get('hasKeys')),
                    ip_address=str(info.get('ipAddress') or ''),
                    port=int(info.get('port') or 6444),
                )
            except (TypeError, ValueError):
                _LOGGER.warning('Invalid known appliance ignored: %s', device_id)
        only_device_id = message.get('onlyDeviceId')
        return cls(
            account=str(message.get('account') or '').strip(),
            password=str(message.get('password') or ''),
            broadcast_addresses=tuple(a.strip() for a in str(message.get('broadcastAddress') or '').split(',') if a.strip()),
            known_devices=known,
            only_device_id=int(only_device_id) if only_device_id not in (None, '') else None,
            force_keys=bool(message.get('forceKeys')),
        )


ProgressCallback = Callable[[str], Awaitable[None]]


class SyncService:

    def __init__(self, guard: CloudGuard, *, discover_fn=discover, check_keys_fn=check_keys, cloud_session_factory=CloudSession) -> None:
        self._guard = guard
        self._discover = discover_fn
        self._check_keys = check_keys_fn
        self._cloud_session_factory = cloud_session_factory

    async def run(self, request: SyncRequest, progress: ProgressCallback) -> dict[str, Any]:
        await progress('discovery')
        lan_devices = await self._discover_lan(request)
        devices: dict[int, dict[str, Any]] = {}
        for lan_device in lan_devices.values():
            self._merge_lan(devices, lan_device)

        cloud_error = None
        if request.account:
            await progress('cloudLogin')
            try:
                async with self._cloud_session_factory(request.account, request.password, self._guard) as cloud:
                    await progress('cloudDevices')
                    for appliance in await cloud.list_appliances():
                        if request.only_device_id is None or appliance.appliance_id == request.only_device_id:
                            self._merge_cloud(devices, appliance)
                    await progress('keys')
                    for device in devices.values():
                        await self._fill_keys(device, request, cloud)
            except CloudError as error:
                _LOGGER.error('MSmartHome cloud: %s', error)
                cloud_error = error.to_jeedom()
        for device in devices.values():
            if 'keysStatus' not in device:
                self._set_status_without_cloud(device, request, cloud_error)

        _LOGGER.info('Synchronization done: %s appliance(s)', len(devices))
        return {
            'devices': list(devices.values()),
            'cloudError': cloud_error,
            'onlyDeviceId': str(request.only_device_id) if request.only_device_id is not None else None,
        }

    async def _discover_lan(self, request: SyncRequest) -> dict[int, LanDevice]:
        addresses = list(request.broadcast_addresses)
        if request.only_device_id is not None:
            known = request.known_devices.get(request.only_device_id)
            if known is not None and known.ip_address:
                # Ask the appliance directly, it also works across subnets
                addresses = [known.ip_address]
        found = await self._discover(addresses)
        if request.only_device_id is not None:
            found = {k: v for k, v in found.items() if k == request.only_device_id}
        return found

    @staticmethod
    def _base_device(device_id: int, device_type: int) -> dict[str, Any]:
        return {
            'deviceId': str(device_id),
            'deviceType': device_type_code(device_type),
            'supported': device_type in SUPPORTED_DEVICE_TYPES,
            'name': '',
            'serialNumber': '',
            'model': '',
            'ipAddress': '',
            'port': None,
            'protocolVersion': None,
            'inCloud': False,
            'onLan': False,
            'online': None,
            'token': '',
            'key': '',
        }

    def _merge_lan(self, devices: dict[int, dict[str, Any]], lan_device: LanDevice) -> None:
        device = devices.setdefault(lan_device.device_id, self._base_device(lan_device.device_id, lan_device.device_type))
        device.update({
            'ipAddress': lan_device.ip_address,
            'port': lan_device.port,
            'protocolVersion': lan_device.protocol_version,
            'onLan': True,
            'serialNumber': device['serialNumber'] or lan_device.serial_number,
            'model': device['model'] or lan_device.model,
        })

    def _merge_cloud(self, devices: dict[int, dict[str, Any]], appliance: CloudAppliance) -> None:
        device = devices.setdefault(appliance.appliance_id, self._base_device(appliance.appliance_id, appliance.device_type))
        device.update({
            'name': appliance.name,
            'inCloud': True,
            'online': appliance.online,
            'serialNumber': appliance.serial_number or device['serialNumber'],
            'model': appliance.model or device['model'],
        })

    def _status_before_keys(self, device: dict[str, Any], request: SyncRequest) -> str | None:
        """Status when no cloud key request is needed, None when keys must be fetched."""
        known = request.known_devices.get(int(device['deviceId']))
        if not device['supported']:
            return KeysStatus.UNSUPPORTED
        if device['protocolVersion'] is not None and device['protocolVersion'] < 3:
            return KeysStatus.NOT_NEEDED
        if known is not None and known.has_keys and not request.force_keys:
            return KeysStatus.KNOWN
        return None

    async def _fill_keys(self, device: dict[str, Any], request: SyncRequest, cloud: CloudSession) -> None:
        status = self._status_before_keys(device, request)
        if status is not None:
            device['keysStatus'] = status
            return
        if not device['inCloud']:
            device['keysStatus'] = KeysStatus.NOT_IN_CLOUD
            return
        device_id = int(device['deviceId'])
        known = request.known_devices.get(device_id)
        ip_address = device['ipAddress'] or (known.ip_address if known else '')
        port = device['port'] or (known.port if known else 6444)
        if not ip_address:
            device['keysStatus'] = KeysStatus.NOT_ON_LAN
            return
        try:
            candidates = await cloud.get_key_candidates(device_id)
        except CloudError as error:
            _LOGGER.warning('Keys of the appliance %s not retrieved: %s', device_id, error)
            device['keysStatus'] = KeysStatus.NOT_OWNED if error.reason == 'notOwned' else KeysStatus.CLOUD_ERROR
            return
        if not candidates:
            device['keysStatus'] = KeysStatus.CLOUD_ERROR
            return
        status, keys = await self._check_keys(ip_address, port, device_id, candidates)
        device['keysStatus'] = status
        if keys is not None:
            device['token'], device['key'] = keys
            device['protocolVersion'] = 3

    def _set_status_without_cloud(self, device: dict[str, Any], request: SyncRequest, cloud_error: dict | None) -> None:
        status = self._status_before_keys(device, request)
        if status is None:
            status = KeysStatus.CLOUD_ERROR if cloud_error else KeysStatus.NO_ACCOUNT
        device['keysStatus'] = status

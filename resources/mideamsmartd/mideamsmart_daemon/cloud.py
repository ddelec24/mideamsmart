"""Access to the MSmartHome cloud, used only to list the appliances and get their keys.

Every login counts for the Midea anti-abuse protection (errors 7610 / 65027 can
lock the account up to 24 h), so the daemon logs in only when the user asks
for a synchronization, and CloudGuard refuses new logins after such errors.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any

import aiohttp
from midealocal.cloud import get_midea_cloud
from midealocal.exceptions import CloudLoginError, MideaCloudError, NoDeviceRegistered

_LOGGER = logging.getLogger(__name__)

CLOUD_NAME = 'SmartHome'
REQUEST_TIMEOUT = 30

# Minimum delay between two logins, and lockouts applied after the cloud protections
MIN_LOGIN_INTERVAL = 30
LOCKOUT_DELAYS = {
    7610: 15 * 60,  # too many failed logins
    65027: 60 * 60,  # too many simultaneous logins
}
INVALID_CREDENTIALS_CODES = frozenset({3101, 3102})


class CloudError(Exception):
    """Cloud failure, with a stable reason sent to Jeedom (translated there)."""

    def __init__(self, reason: str, cloud_code: int | None = None, retry_after: int = 0) -> None:
        super().__init__(f'{reason} (code {cloud_code})' if cloud_code else reason)
        self.reason = reason
        self.cloud_code = cloud_code
        self.retry_after = retry_after

    def to_jeedom(self) -> dict[str, Any]:
        return {'reason': self.reason, 'cloudCode': self.cloud_code, 'retryAfter': self.retry_after}


@dataclass(frozen=True)
class CloudAppliance:
    appliance_id: int
    name: str
    device_type: int
    serial_number: str
    model: str
    online: bool


class CloudGuard:
    """Remembers the cloud refusals to avoid getting the account locked."""

    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._last_login = None
        self._locked_until = 0.0
        self._lock_code: int | None = None
        self._rejected_credentials: str | None = None

    @staticmethod
    def _fingerprint(account: str, password: str) -> str:
        return hashlib.sha256(f'{account}\0{password}'.encode()).hexdigest()

    def check(self, account: str, password: str) -> None:
        """Raises CloudError when a login must not be attempted now."""
        now = self._clock()
        if self._rejected_credentials == self._fingerprint(account, password):
            raise CloudError('invalidCredentials')
        if now < self._locked_until:
            raise CloudError('accountLocked', self._lock_code, int(self._locked_until - now) + 1)
        if self._last_login is not None and now - self._last_login < MIN_LOGIN_INTERVAL:
            raise CloudError('tooFrequent', retry_after=int(MIN_LOGIN_INTERVAL - (now - self._last_login)) + 1)

    def record_attempt(self) -> None:
        self._last_login = self._clock()

    def record_error(self, code: int | None, account: str, password: str) -> None:
        if code in INVALID_CREDENTIALS_CODES:
            self._rejected_credentials = self._fingerprint(account, password)
        elif code in LOCKOUT_DELAYS:
            self._locked_until = self._clock() + LOCKOUT_DELAYS[code]
            self._lock_code = code

    def record_success(self) -> None:
        self._rejected_credentials = None
        self._locked_until = 0.0
        self._lock_code = None


class CloudSession:
    """One logged-in MSmartHome session, to be used as an async context manager."""

    def __init__(self, account: str, password: str, guard: CloudGuard) -> None:
        self._account = account
        self._password = password
        self._guard = guard
        self._http: aiohttp.ClientSession | None = None
        self._cloud = None

    async def __aenter__(self) -> 'CloudSession':
        self._guard.check(self._account, self._password)
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT))
        self._cloud = get_midea_cloud(CLOUD_NAME, self._http, self._account, self._password)
        self._guard.record_attempt()
        try:
            logged_in = await self._cloud.login()
        except CloudLoginError as error:
            self._guard.record_error(error.code, self._account, self._password)
            await self._close()
            raise self._login_error(error.code) from error
        except MideaCloudError as error:
            await self._close()
            raise CloudError('cloudError', error.code) from error
        except (aiohttp.ClientError, TimeoutError) as error:
            await self._close()
            raise CloudError('cloudUnreachable') from error
        if not logged_in:
            await self._close()
            raise CloudError('loginFailed')
        self._guard.record_success()
        _LOGGER.info('Logged in to the MSmartHome cloud')
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self._close()

    async def _close(self) -> None:
        if self._http is not None:
            await self._http.close()
            self._http = None

    @staticmethod
    def _login_error(code: int) -> CloudError:
        if code in INVALID_CREDENTIALS_CODES:
            return CloudError('invalidCredentials', code)
        if code in LOCKOUT_DELAYS:
            return CloudError('accountLocked', code, LOCKOUT_DELAYS[code])
        return CloudError('loginFailed', code)

    async def list_appliances(self) -> list[CloudAppliance]:
        try:
            appliances = await self._cloud.list_appliances(None)
        except MideaCloudError as error:
            raise CloudError('cloudError', error.code) from error
        except (aiohttp.ClientError, TimeoutError) as error:
            raise CloudError('cloudUnreachable') from error
        if appliances is None:
            raise CloudError('cloudError')
        result = []
        for appliance_id, info in appliances.items():
            result.append(CloudAppliance(
                appliance_id=int(appliance_id),
                name=str(info.get('name') or ''),
                device_type=int(info.get('type') or 0),
                serial_number=str(info.get('sn') or ''),
                model=str(info.get('sn8') or info.get('model') or ''),
                online=bool(info.get('online')),
            ))
        _LOGGER.info('%s appliance(s) found in the MSmartHome account', len(result))
        return result

    async def get_key_candidates(self, appliance_id: int) -> list[tuple[str, str]]:
        """Token/key pairs proposed by the cloud (one per udpid method), to be checked on the LAN."""
        try:
            keys = await self._cloud.get_cloud_keys(appliance_id)
        except NoDeviceRegistered as error:
            raise CloudError('notOwned', error.code) from error
        except MideaCloudError as error:
            raise CloudError('cloudError', error.code) from error
        except (aiohttp.ClientError, TimeoutError) as error:
            raise CloudError('cloudUnreachable') from error
        return [(value['token'], value['key']) for _, value in sorted(keys.items()) if value.get('token') and value.get('key')]

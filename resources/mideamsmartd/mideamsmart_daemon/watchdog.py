"""Finds again on the local network the appliances that stopped answering (new DHCP lease).

Only the LAN discovery is used, never the cloud.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from .discovery import discover

_LOGGER = logging.getLogger(__name__)

CHECK_PERIOD = 60
# An appliance is searched once it has not answered for this delay
OFFLINE_DELAY = 300
# Minimum delay between two searches
SEARCH_INTERVAL = 600


class AddressWatchdog:

    def __init__(self, device_manager, send_event: Callable[[dict[str, Any]], Awaitable[None]], *,
                 discover_fn=discover, clock=time.monotonic) -> None:
        self._device_manager = device_manager
        self._send_event = send_event
        self._discover = discover_fn
        self._clock = clock
        self._last_search: float | None = None
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name='address-watchdog')

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(CHECK_PERIOD)
            try:
                await self.check()
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception('Error while searching the offline appliances')

    def _offline_drivers(self) -> list:
        now = self._clock()
        return [driver for driver in self._device_manager.drivers.values()
                if driver.offline_since is not None and now - driver.offline_since >= OFFLINE_DELAY]

    async def check(self) -> None:
        offline = self._offline_drivers()
        if not offline:
            return
        now = self._clock()
        if self._last_search is not None and now - self._last_search < SEARCH_INTERVAL:
            return
        self._last_search = now
        _LOGGER.info('Searching %s offline appliance(s) on the local network', len(offline))
        found = await self._discover(list(self._device_manager.broadcast_addresses))
        for driver in offline:
            config = driver.config
            lan_device = found.get(config.device_id)
            if lan_device is None:
                continue
            if (lan_device.ip_address, lan_device.port) == (config.ip_address, config.port):
                continue
            _LOGGER.warning('[%s] Appliance found at a new address: %s:%s (was %s:%s)', config.label,
                            lan_device.ip_address, lan_device.port, config.ip_address or '?', config.port)
            await self._send_event({'action': 'deviceAddressChanged', 'eqLogicId': config.eq_logic_id,
                                    'ipAddress': lan_device.ip_address, 'port': lan_device.port})

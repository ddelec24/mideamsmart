"""Device drivers, indexed by Midea device type."""

from .ac import AcDriver
from .base import BaseDriver, CommandError
from .cc import CcDriver

DRIVERS: dict[str, type[BaseDriver]] = {
    'AC': AcDriver,
    'CC': CcDriver,
}

__all__ = ['DRIVERS', 'BaseDriver', 'CommandError']

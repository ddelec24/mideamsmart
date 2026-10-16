"""Device drivers, indexed by Midea device type."""

from .a1 import A1Driver
from .ac import AcDriver
from .base import BaseDriver, CommandError
from .cc import CcDriver

DRIVERS: dict[str, type[BaseDriver]] = {
    'AC': AcDriver,
    'CC': CcDriver,
    'A1': A1Driver,
}

__all__ = ['DRIVERS', 'BaseDriver', 'CommandError']

"""ArvanCloud Object Storage — simple library and CLI."""

from r1cmd.constants import APP_NAME, ARVAN_STORAGE_ENDPOINT
from r1cmd.core import ArvanStorage, ArvanStorageConfig, ArvanStorageError, RemoteFile

__all__ = [
    "APP_NAME",
    "ARVAN_STORAGE_ENDPOINT",
    "ArvanStorage",
    "ArvanStorageConfig",
    "ArvanStorageError",
    "RemoteFile",
]
__version__ = "0.2.0"

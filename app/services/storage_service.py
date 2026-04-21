"""
Storage backends — local filesystem now, S3 later.

The active backend is selected via the STORAGE_PROVIDER env var.
"""

import os
import shutil
from abc import ABC, abstractmethod
from typing import BinaryIO

from dotenv import load_dotenv

load_dotenv()

STORAGE_LOCAL_PATH = os.getenv("STORAGE_LOCAL_PATH", "./storage/audio")


class StorageBackend(ABC):
    """Abstract interface every storage provider must implement."""

    @abstractmethod
    def save(self, file: BinaryIO, path: str) -> str:
        """Persist *file* at *path* and return the stored path / key."""
        ...

    @abstractmethod
    def load(self, path: str) -> bytes | None:
        """Read and return object bytes from *path* (or None if missing)."""
        ...

    @abstractmethod
    def delete(self, path: str) -> None:
        """Remove the object at *path*."""
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        ...


class LocalStorageBackend(StorageBackend):
    """Stores files on the local filesystem under STORAGE_LOCAL_PATH."""

    def __init__(self, root: str = STORAGE_LOCAL_PATH):
        self.root = root

    def _full(self, path: str) -> str:
        return os.path.join(self.root, path)

    def save(self, file: BinaryIO, path: str) -> str:
        full = self._full(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as out:
            shutil.copyfileobj(file, out)
        return path

    def load(self, path: str) -> bytes | None:
        full = self._full(path)
        if not os.path.isfile(full):
            return None
        with open(full, "rb") as source:
            return source.read()

    def delete(self, path: str) -> None:
        full = self._full(path)
        if os.path.isfile(full):
            os.remove(full)

    def exists(self, path: str) -> bool:
        return os.path.isfile(self._full(path))


# --------------------------------------------------------------------------
# Future S3 backend placeholder
# --------------------------------------------------------------------------
# class S3StorageBackend(StorageBackend):
#     """Upload / delete from an S3-compatible bucket."""
#     def __init__(self, bucket: str, ...): ...


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------

_BACKENDS = {
    "local": LocalStorageBackend,
    # "s3": S3StorageBackend,
}


def get_storage_backend() -> StorageBackend:
    provider = os.getenv("STORAGE_PROVIDER", "local")
    cls = _BACKENDS.get(provider)
    if cls is None:
        raise RuntimeError(f"Unknown STORAGE_PROVIDER '{provider}'. Available: {list(_BACKENDS)}")
    return cls()

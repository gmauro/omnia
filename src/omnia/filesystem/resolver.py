"""Safe resolution of Omnia objects to local POSIX file descriptors."""

from __future__ import annotations

import os
import stat
from pathlib import Path


class StorageRootError(ValueError):
    """Raised when a registered path is not safe to expose through a mount."""


class PosixObjectResolver:
    """Resolve registered object IDs beneath explicit, trusted storage roots.

    This class is intentionally independent of MongoDB.  The caller supplies
    the registered object-id/path mapping while loading a mount view.
    """

    def __init__(self, storage_roots: list[str | Path]):
        if not storage_roots:
            raise StorageRootError("At least one storage root is required")
        self._roots = [Path(root).resolve(strict=True) for root in storage_roots]
        if any(not root.is_dir() for root in self._roots):
            raise StorageRootError("Storage roots must be existing directories")
        self._paths: dict[str, Path] = {}

    def register(self, object_id: str, path: str | Path) -> None:
        candidate = Path(path)
        if not candidate.is_absolute():
            raise StorageRootError(f"{object_id}: registered path is not absolute")
        root = self._matching_root(candidate)
        self._reject_symlinks(root, candidate)
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as error:
            raise StorageRootError(f"{object_id}: registered file does not exist") from error
        if not resolved.is_file():
            raise StorageRootError(f"{object_id}: registered path is not a regular file")
        self._paths[object_id] = resolved

    def _matching_root(self, candidate: Path) -> Path:
        for root in self._roots:
            try:
                candidate.relative_to(root)
                return root
            except ValueError:
                continue
        raise StorageRootError(f"Registered path is outside allowed storage roots: {candidate}")

    @staticmethod
    def _reject_symlinks(root: Path, candidate: Path) -> None:
        relative = candidate.relative_to(root)
        current = root
        if current.is_symlink():
            raise StorageRootError(f"Storage root must not be a symlink: {root}")
        for component in relative.parts:
            current = current / component
            if current.is_symlink():
                raise StorageRootError(f"Registered path contains a symlink: {candidate}")

    def open(self, object_id: str) -> int:
        try:
            path = self._paths[object_id]
        except KeyError as error:
            raise FileNotFoundError(object_id) from error
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        file_descriptor = os.open(path, flags)
        file_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            os.close(file_descriptor)
            raise StorageRootError(f"{object_id}: object is no longer a regular file")
        return file_descriptor

    def size(self, object_id: str) -> int:
        """Return the current backing-file size without revealing its path."""
        try:
            return self._paths[object_id].stat().st_size
        except KeyError as error:
            raise FileNotFoundError(object_id) from error

    def export_path(self, object_id: str) -> Path:
        """Return a validated backing path for a local symlink export."""
        try:
            return self._paths[object_id]
        except KeyError as error:
            raise FileNotFoundError(object_id) from error

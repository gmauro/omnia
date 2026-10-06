"""Read-only virtual filesystem support for Omnia."""

from .resolver import PosixObjectResolver, StorageRootError
from .virtual_tree import AliasEntry, DatasetEntry, OmniaVirtualTree

__all__ = ["AliasEntry", "DatasetEntry", "OmniaVirtualTree", "PosixObjectResolver", "StorageRootError"]

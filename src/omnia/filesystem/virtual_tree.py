"""A dependency-free virtual tree used by the Omnia FUSE adapter.

The tree deliberately stores dataset identifiers and metadata, not backing
paths.  Backing paths remain in the resolver and are never part of a virtual
filesystem name.
"""

from __future__ import annotations

import datetime as dt
import posixpath
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class DatasetEntry:
    """The minimum registered metadata needed to expose one virtual file."""

    object_id: str
    name: str
    size: int
    modified_at: dt.datetime | None = None
    relative_path: str | None = None


@dataclass(frozen=True)
class AliasEntry:
    """A logical symlink whose target remains inside the virtual tree."""

    relative_path: str
    target_path: str


@dataclass(frozen=True)
class VirtualNode:
    """A virtual directory or a virtual regular file."""

    inode: int
    is_directory: bool
    entry: DatasetEntry | None = None
    alias: AliasEntry | None = None
    content: bytes | None = None


class OmniaVirtualTree:
    """A read-only view of registered objects.

    Entries with ``relative_path`` retain their hierarchy.  Flat catalogue
    entries retain their basename when it is unique; a deterministic object-id
    suffix prevents filename collisions from masking a dataset.
    """

    def __init__(
        self,
        entries: Iterable[DatasetEntry],
        directories: Iterable[str] = (),
        aliases: Iterable[AliasEntry] = (),
        metadata_files: dict[str, bytes] | None = None,
    ):
        self._nodes: dict[PurePosixPath, VirtualNode] = {PurePosixPath("/"): VirtualNode(1, True)}
        self._children: dict[PurePosixPath, list[str]] = {PurePosixPath("/"): []}

        ordered = sorted(entries, key=lambda entry: (entry.relative_path or entry.name, entry.object_id))
        names: dict[str, int] = {}
        for entry in (entry for entry in ordered if entry.relative_path is None):
            base_name = self._safe_basename(entry.name)
            names[base_name] = names.get(base_name, 0) + 1

        next_inode = 2

        def ensure_directory(path: PurePosixPath) -> None:
            nonlocal next_inode
            current = PurePosixPath("/")
            for part in path.parts[1:]:
                current = current / part
                if current not in self._nodes:
                    self._nodes[current] = VirtualNode(next_inode, True)
                    self._children[current] = []
                    self._children[current.parent].append(part)
                    next_inode += 1

        for directory in sorted(directories, key=str.casefold):
            ensure_directory(self._logical_path(directory))

        for relative_path, content in sorted((metadata_files or {}).items(), key=lambda item: item[0].casefold()):
            path = self._logical_path(relative_path)
            ensure_directory(path.parent)
            if path in self._nodes:
                raise ValueError(f"Duplicate virtual path: {path}")
            self._nodes[path] = VirtualNode(next_inode, False, content=content)
            self._children[path.parent].append(path.name)
            next_inode += 1

        for alias in sorted(aliases, key=lambda item: item.relative_path.casefold()):
            path = self._logical_path(alias.relative_path)
            self._logical_path(alias.target_path)
            ensure_directory(path.parent)
            if path in self._nodes:
                raise ValueError(f"Duplicate virtual path: {path}")
            self._nodes[path] = VirtualNode(next_inode, False, alias=alias)
            self._children[path.parent].append(path.name)
            next_inode += 1

        for entry in ordered:
            if entry.relative_path is None:
                base_name = self._safe_basename(entry.name)
                visible_name = f"{base_name}--{entry.object_id}" if names[base_name] > 1 else base_name
                path = PurePosixPath("/") / visible_name
            else:
                path = self._logical_path(entry.relative_path)
            ensure_directory(path.parent)
            if path in self._nodes:
                raise ValueError(f"Duplicate virtual path: {path}")
            self._nodes[path] = VirtualNode(next_inode, False, entry)
            self._children[path.parent].append(path.name)
            next_inode += 1

        for children in self._children.values():
            children.sort(key=str.casefold)

    @staticmethod
    def _safe_basename(name: str) -> str:
        """Return one safe virtual filename, never a client-controlled path."""
        base_name = PurePosixPath(name).name
        if base_name in ("", ".", ".."):
            return "unnamed"
        return base_name.replace("/", "_")

    @classmethod
    def _logical_path(cls, relative_path: str) -> PurePosixPath:
        logical = PurePosixPath(relative_path)
        if logical.is_absolute() or ".." in logical.parts or logical in (PurePosixPath("."), PurePosixPath("")):
            raise ValueError(f"Unsafe logical path: {relative_path}")
        return PurePosixPath("/") / logical

    @staticmethod
    def normalise(path: str) -> PurePosixPath:
        path = PurePosixPath(path)
        if not path.is_absolute():
            path = PurePosixPath("/") / path
        if ".." in path.parts:
            raise FileNotFoundError(path)
        return path

    def node(self, path: str) -> VirtualNode:
        path_obj = self.normalise(path)
        try:
            return self._nodes[path_obj]
        except KeyError as error:
            raise FileNotFoundError(path) from error

    def children(self, path: str) -> list[str]:
        node = self.node(path)
        if not node.is_directory:
            raise NotADirectoryError(path)
        return list(self._children[self.normalise(path)])

    def stat(self, path: str) -> dict[str, int | float]:
        node = self.node(path)
        now = dt.datetime.now().timestamp()
        if node.is_directory:
            return {
                "st_mode": stat.S_IFDIR | 0o555,
                "st_nlink": 2,
                "st_size": 0,
                "st_ctime": now,
                "st_mtime": now,
                "st_atime": now,
                "st_ino": node.inode,
            }

        if node.alias is not None:
            target = self.alias_target(path)
            return {
                "st_mode": stat.S_IFLNK | 0o777,
                "st_nlink": 1,
                "st_size": len(target),
                "st_ctime": now,
                "st_mtime": now,
                "st_atime": now,
                "st_ino": node.inode,
            }

        if node.content is not None:
            return {
                "st_mode": stat.S_IFREG | 0o444,
                "st_nlink": 1,
                "st_size": len(node.content),
                "st_ctime": now,
                "st_mtime": now,
                "st_atime": now,
                "st_ino": node.inode,
            }

        assert node.entry is not None
        timestamp = node.entry.modified_at.timestamp() if node.entry.modified_at else now
        return {
            "st_mode": stat.S_IFREG | 0o444,
            "st_nlink": 1,
            "st_size": node.entry.size,
            "st_ctime": timestamp,
            "st_mtime": timestamp,
            "st_atime": timestamp,
            "st_ino": node.inode,
        }

    def alias_target(self, path: str) -> str:
        """Return a relative, virtual target suitable for FUSE ``readlink``."""
        path_obj = self.normalise(path)
        node = self.node(path)
        if node.alias is None:
            raise OSError("Not a symbolic link")
        target = self._logical_path(node.alias.target_path)
        return posixpath.relpath(str(target), start=str(path_obj.parent))

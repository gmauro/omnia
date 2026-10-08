"""Optional fusepy adapter for an :class:`OmniaVirtualTree`."""

from __future__ import annotations

import errno
import os

from .resolver import PosixObjectResolver
from .virtual_tree import OmniaVirtualTree


def mount(tree: OmniaVirtualTree, resolver: PosixObjectResolver, mountpoint: str, foreground: bool = True) -> None:
    """Mount a read-only Omnia view, importing fusepy only when needed."""
    try:
        from fuse import FUSE, FuseOSError, Operations
    except ImportError as error:
        raise RuntimeError("FUSE support is not installed. Install Omnia with `omnia[fuse]`.") from error

    class OmniaFuseOperations(Operations):
        def __init__(self):
            self._virtual_handles: dict[int, bytes] = {}
            self._next_virtual_handle = 1_000_000

        def getattr(self, path, fh=None):
            try:
                return tree.stat(path)
            except FileNotFoundError as error:
                raise FuseOSError(errno.ENOENT) from error

        def readdir(self, path, fh):
            try:
                return [".", "..", *tree.children(path)]
            except FileNotFoundError as error:
                raise FuseOSError(errno.ENOENT) from error
            except NotADirectoryError as error:
                raise FuseOSError(errno.ENOTDIR) from error

        def open(self, path, flags):
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC):
                raise FuseOSError(errno.EROFS)
            try:
                node = tree.node(path)
                if node.is_directory:
                    raise FuseOSError(errno.EISDIR)
                if node.content is not None:
                    handle = self._next_virtual_handle
                    self._next_virtual_handle += 1
                    self._virtual_handles[handle] = node.content
                    return handle
                if node.entry is None:
                    raise FuseOSError(errno.EISDIR)
                return resolver.open(node.entry.object_id)
            except FileNotFoundError as error:
                raise FuseOSError(errno.ENOENT) from error
            except OSError as error:
                raise FuseOSError(error.errno or errno.EIO) from error

        def readlink(self, path):
            try:
                return tree.alias_target(path)
            except FileNotFoundError as error:
                raise FuseOSError(errno.ENOENT) from error
            except OSError as error:
                raise FuseOSError(errno.EINVAL) from error

        def read(self, path, size, offset, fh):
            if fh in self._virtual_handles:
                return self._virtual_handles[fh][offset : offset + size]
            return os.pread(fh, size, offset)

        def release(self, path, fh):
            if fh in self._virtual_handles:
                self._virtual_handles.pop(fh)
                return 0
            os.close(fh)
            return 0

        def create(self, path, mode, fi=None):
            raise FuseOSError(errno.EROFS)

        def mkdir(self, path, mode):
            raise FuseOSError(errno.EROFS)

        def unlink(self, path):
            raise FuseOSError(errno.EROFS)

        def rmdir(self, path):
            raise FuseOSError(errno.EROFS)

        def rename(self, old, new):
            raise FuseOSError(errno.EROFS)

        def write(self, path, data, offset, fh):
            raise FuseOSError(errno.EROFS)

    FUSE(OmniaFuseOperations(), mountpoint, foreground=foreground, ro=True, nothreads=True)

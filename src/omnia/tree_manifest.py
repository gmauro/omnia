"""Loading and applying curator-owned logical-tree manifests."""

from __future__ import annotations

import fnmatch
import hashlib
from dataclasses import dataclass
from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml import YAML

from omnia.models.data_tree import TreeEntry, TreeSnapshot


class ManifestError(ValueError):
    """Raised when a curator manifest is malformed or contradicts a tree."""


@dataclass(frozen=True)
class CuratedNode:
    path: str
    role: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LogicalRename:
    """One source-to-logical-path mapping applied while a tree is ingested."""

    source: str
    destination: str


@dataclass(frozen=True)
class CuratorManifest:
    content: str
    checksum: str
    catalog: str | None
    snapshot: str | None
    nodes: tuple[CuratedNode, ...]
    exclude: tuple[str, ...]
    renames: tuple[LogicalRename, ...] = ()

    def excludes(self, relative_path: str) -> bool:
        """Match path patterns consistently for root and nested files."""
        return any(
            fnmatch.fnmatchcase(relative_path, pattern)
            or (pattern.startswith("**/") and fnmatch.fnmatchcase(relative_path, pattern[3:]))
            for pattern in self.exclude
        )

    def logical_path(self, relative_path: str) -> str:
        """Map a scanned physical-relative path to its curated logical path."""
        matches = [
            rename
            for rename in self.renames
            if relative_path == rename.source or relative_path.startswith(f"{rename.source}/")
        ]
        if not matches:
            return relative_path
        rename = max(matches, key=lambda item: len(PurePosixPath(item.source).parts))
        suffix = relative_path.removeprefix(rename.source).lstrip("/")
        return (PurePosixPath(rename.destination) / suffix).as_posix() if suffix else rename.destination


def _relative_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{field} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path in (PurePosixPath("."), PurePosixPath("")):
        raise ManifestError(f"{field} must be a safe relative path: {value!r}")
    return path.as_posix()


def load_manifest(path: Path) -> CuratorManifest:
    """Read and validate the small curator-owned YAML document."""
    content = path.read_text(encoding="utf-8")
    document = YAML(typ="safe").load(content) or {}
    if not isinstance(document, dict):
        raise ManifestError("Manifest root must be a mapping")

    catalog = document.get("catalog")
    snapshot = document.get("snapshot")
    if catalog is not None and not isinstance(catalog, str):
        raise ManifestError("catalog must be a string")
    if snapshot is not None and not isinstance(snapshot, str):
        raise ManifestError("snapshot must be a string")

    nodes: list[CuratedNode] = []
    for index, node in enumerate(document.get("nodes", [])):
        if not isinstance(node, dict):
            raise ManifestError(f"nodes[{index}] must be a mapping")
        node_path = _relative_path(node.get("path"), f"nodes[{index}].path")
        role = node.get("role")
        metadata = node.get("metadata", {})
        if role is not None and not isinstance(role, str):
            raise ManifestError(f"nodes[{index}].role must be a string")
        if not isinstance(metadata, dict):
            raise ManifestError(f"nodes[{index}].metadata must be a mapping")
        nodes.append(CuratedNode(node_path, role, metadata))

    renames: list[LogicalRename] = []
    rename_sources: set[str] = set()
    for index, rename in enumerate(document.get("renames", [])):
        if not isinstance(rename, dict):
            raise ManifestError(f"renames[{index}] must be a mapping")
        source = _relative_path(rename.get("source"), f"renames[{index}].source")
        destination = _relative_path(rename.get("destination"), f"renames[{index}].destination")
        if source in rename_sources:
            raise ManifestError(f"renames[{index}].source is duplicated: {source!r}")
        rename_sources.add(source)
        renames.append(LogicalRename(source, destination))

    exclude = document.get("exclude", [])
    if not isinstance(exclude, list) or not all(isinstance(pattern, str) for pattern in exclude):
        raise ManifestError("exclude must be a list of glob patterns")
    return CuratorManifest(
        content=content,
        checksum=hashlib.sha256(content.encode()).hexdigest(),
        catalog=catalog,
        snapshot=snapshot,
        nodes=tuple(nodes),
        exclude=tuple(exclude),
        renames=tuple(renames),
    )


def retarget_manifest(content: str, snapshot_name: str) -> tuple[str, str]:
    """Return a copy of a stored manifest whose snapshot safeguard is updated."""
    yaml = YAML()
    document = yaml.load(content)
    if not isinstance(document, dict):
        raise ManifestError("Stored manifest root must be a mapping")
    document["snapshot"] = snapshot_name
    output = StringIO()
    yaml.dump(document, output)
    updated_content = output.getvalue()
    return updated_content, hashlib.sha256(updated_content.encode()).hexdigest()


def apply_manifest(snapshot: TreeSnapshot, manifest: CuratorManifest) -> None:
    """Apply curated node annotations only after a scan has built the tree."""
    paths = {entry.relative_path: entry for entry in TreeEntry.objects(snapshot=snapshot)}
    for node in manifest.nodes:
        entry = paths.get(node.path)
        if entry is None:
            raise ManifestError(f"Manifest node does not exist in scanned tree: {node.path}")
        metadata = dict(entry.metadata or {})
        metadata.update(node.metadata)
        if node.role:
            metadata["role"] = node.role
        entry.metadata = metadata
        entry.save()

    snapshot.manifest_content = manifest.content
    snapshot.manifest_sha256 = manifest.checksum
    snapshot.metadata = {
        **(snapshot.metadata or {}),
        "manifest_nodes": len(manifest.nodes),
        "manifest_renames": len(manifest.renames),
    }
    snapshot.save()

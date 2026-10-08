"""Atomic, read-only symlink exports for published logical tree snapshots."""

from __future__ import annotations

import json
import os
import shutil
import stat
import uuid
from pathlib import Path

from omnia.filesystem import PosixObjectResolver
from omnia.models.data_tree import TreeEntry, TreeSnapshot


class ExportError(ValueError):
    """Raised when a snapshot cannot be safely materialized as links."""


def _relative_link(target: Path, link_path: Path) -> str:
    return os.path.relpath(target, start=link_path.parent)


def _is_in_subtree(path: str, root: str) -> bool:
    return path == root or path.startswith(f"{root}/")


def _filter_modality(entries: list[TreeEntry], modality: str) -> list[TreeEntry]:
    """Select curated modality subtrees, retaining only internal aliases."""
    roots = [
        entry.relative_path
        for entry in entries
        if (entry.metadata or {}).get("role") == "modality"
        and (entry.metadata or {}).get("modality", "").casefold() == modality.casefold()
    ]
    if not roots:
        raise ExportError(f"No modality '{modality}' is defined in this snapshot")

    selected = [entry for entry in entries if any(_is_in_subtree(entry.relative_path, root) for root in roots)]
    selected_paths = {entry.relative_path for entry in selected}
    return [entry for entry in selected if entry.kind != "alias" or entry.target_path in selected_paths]


def export_links(
    snapshot: TreeSnapshot,
    destination: Path,
    storage_roots: list[str | Path],
    modality: str | None = None,
) -> None:
    """Materialize a published snapshot as an atomically-created symlink tree."""
    if snapshot.state == "retired":
        raise ExportError("Retired snapshots cannot be exported")
    if snapshot.state != "published":
        raise ExportError("Only published snapshots can be exported")
    if destination.exists() or destination.is_symlink():
        raise ExportError(f"Destination already exists: {destination}")
    if not destination.parent.is_dir():
        raise ExportError(f"Destination parent does not exist: {destination.parent}")

    entries = list(TreeEntry.objects(snapshot=snapshot))
    if modality:
        entries = _filter_modality(entries, modality)
    paths = {entry.relative_path for entry in entries}
    resolver = PosixObjectResolver(storage_roots)
    for entry in entries:
        if entry.kind == "file":
            if entry.dataset is None:
                raise ExportError(f"File entry has no dataset: {entry.relative_path}")
            resolver.register(entry.dataset.uk, entry.dataset.path)
        elif entry.kind == "alias" and (not entry.target_path or entry.target_path not in paths):
            raise ExportError(f"Alias target is missing: {entry.relative_path}")

    staging = destination.parent / f".{destination.name}.omnia-{uuid.uuid4().hex}.tmp"
    try:
        staging.mkdir()
        directories = sorted(
            (entry for entry in entries if entry.kind == "directory"), key=lambda item: item.relative_path
        )
        for entry in directories:
            (staging / entry.relative_path).mkdir(parents=True, exist_ok=False)

        files = (entry for entry in entries if entry.kind == "file")
        for entry in files:
            link_path = staging / entry.relative_path
            link_path.parent.mkdir(parents=True, exist_ok=True)
            target = resolver.export_path(entry.dataset.uk)
            link_path.symlink_to(_relative_link(target, link_path))

        aliases = (entry for entry in entries if entry.kind == "alias")
        for entry in aliases:
            link_path = staging / entry.relative_path
            link_path.parent.mkdir(parents=True, exist_ok=True)
            virtual_target = staging / entry.target_path
            link_path.symlink_to(_relative_link(virtual_target, link_path))

        (staging / ".omnia-snapshot.json").write_text(
            json.dumps(
                {
                    "catalog": snapshot.collection.name,
                    "snapshot": snapshot.name,
                    "snapshot_id": str(snapshot.id),
                    "manifest_sha256": snapshot.manifest_sha256,
                    "modality": modality,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        # The owner needs write permission on a directory to remove a local
        # export.  Symlink targets remain untouched by changes to this view.
        directory_mode = (
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        for directory, _, _ in os.walk(staging):
            Path(directory).chmod(directory_mode)
        os.replace(staging, destination)
    except Exception:
        if staging.exists():
            for directory, _, _ in os.walk(staging):
                Path(directory).chmod(stat.S_IRWXU)
            shutil.rmtree(staging)
        raise

"""Describe the Omnia logical location containing a local path."""

from __future__ import annotations

import json
from pathlib import Path

import click
import cloup
from mongoengine.errors import DoesNotExist

from omnia.cli.browse import OUTPUT_FORMAT, _catalog, _emit, _iso, _snapshot, _text
from omnia.models.data_tree import TreeEntry
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri

MARKER_NAME = ".omnia-snapshot.json"


def _view_context(path: Path) -> tuple[Path, dict[str, object], str]:
    """Find the nearest Omnia marker without resolving user symlinks."""
    absolute = path.absolute()
    search_from = absolute if absolute.is_dir() else absolute.parent
    for candidate in (search_from, *search_from.parents):
        marker = candidate / MARKER_NAME
        if marker.is_file():
            try:
                document = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise click.ClickException(f"Invalid Omnia view marker: {marker}") from error
            catalog = document.get("catalog")
            snapshot = document.get("snapshot")
            if not isinstance(catalog, str) or not isinstance(snapshot, str):
                raise click.ClickException(f"Invalid Omnia view marker: {marker}")
            try:
                logical_path = absolute.relative_to(candidate).as_posix()
            except ValueError as error:
                raise click.ClickException(f"Path is outside the Omnia view: {absolute}") from error
            return candidate, document, "" if logical_path == "." else logical_path
    raise click.ClickException(
        "This path is not inside an Omnia snapshot view. "
        "Use 'omnia browse ...' to locate a published snapshot, then mount or export it."
    )


def _subtree_entries(snapshot, logical_path: str) -> list[TreeEntry]:
    entries = list(TreeEntry.objects(snapshot=snapshot))
    if not logical_path:
        return entries
    prefix = f"{logical_path}/"
    return [entry for entry in entries if entry.relative_path == logical_path or entry.relative_path.startswith(prefix)]


@cloup.command(
    "describe", no_args_is_help=False, help="Describe the Omnia logical data at PATH or the current directory."
)
@cloup.argument("path", required=False, default=".", type=click.Path(path_type=Path))
@cloup.option("--format", "output_format", type=OUTPUT_FORMAT, default="table", show_default=True)
def describe_path(path: Path, output_format: str) -> None:
    """Describe PATH from its logical level downwards inside an Omnia view."""
    _, marker, logical_path = _view_context(path)
    collection_name = marker["catalog"]
    snapshot_name = marker["snapshot"]
    with get_mec(uri=get_mongo_uri()):
        snapshot = _snapshot(_catalog(collection_name), snapshot_name, include_retired=True)
        entry = TreeEntry.objects(snapshot=snapshot, relative_path=logical_path).first() if logical_path else None
        if logical_path and not entry:
            raise click.ClickException(f"Logical path '{logical_path}' was not found in its Omnia snapshot.")
        descendants = _subtree_entries(snapshot, logical_path)
        known_size = 0
        unknown_size = False
        for descendant in descendants:
            if descendant.kind != "file":
                continue
            try:
                dataset = descendant.dataset
            except DoesNotExist:
                dataset = None
            size = dataset.size if dataset else None
            if size is None:
                unknown_size = True
            else:
                known_size += size
        modalities = sorted(
            {
                (descendant.metadata or {}).get("modality")
                for descendant in descendants
                if (descendant.metadata or {}).get("role") == "modality" and (descendant.metadata or {}).get("modality")
            }
        )
        row: dict[str, object] = {
            "catalog": snapshot.collection.name,
            "snapshot": snapshot.name,
            "snapshot_state": snapshot.state,
            "logical_path": logical_path or "/",
            "kind": entry.kind if entry else "directory",
            "metadata": entry.metadata if entry and entry.metadata else {},
            "files": sum(descendant.kind == "file" for descendant in descendants),
            "directories": sum(descendant.kind == "directory" for descendant in descendants),
            "aliases": sum(descendant.kind == "alias" for descendant in descendants),
            "known_size_bytes": known_size,
            "size_complete": not unknown_size,
            "modalities": modalities,
            "manifest_sha256": snapshot.manifest_sha256,
            "published": _iso(snapshot.published_at),
        }
        if entry and entry.kind == "file":
            try:
                dataset = entry.dataset
            except DoesNotExist:
                dataset = None
            row.update(
                {
                    "dataset_id": dataset.uk if dataset else None,
                    "checksum": dataset.checksum if dataset else None,
                    "encoding_format": dataset.encoding_format if dataset else None,
                    "status": "available" if dataset else "dataset deleted",
                }
            )
        if entry and entry.kind == "alias":
            row["target_path"] = entry.target_path
    if output_format == "table":
        for key, value in row.items():
            click.echo(f"{key}: {_text(value)}")
    else:
        _emit([row], list(row), output_format)

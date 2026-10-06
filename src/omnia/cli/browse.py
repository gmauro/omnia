"""Read-only catalogue discovery commands for data consumers."""

from __future__ import annotations

import fnmatch
import json
from collections.abc import Iterable
from pathlib import PurePosixPath
from typing import Any

import click
import cloup
from mongoengine.errors import DoesNotExist

from omnia.models.data_collection import Datacatalog
from omnia.models.data_tree import TreeEntry, TreeSnapshot
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri

OUTPUT_FORMAT = click.Choice(("table", "tsv", "json"), case_sensitive=False)


def _text(value: object) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, dict | list):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _emit(rows: Iterable[dict[str, Any]], columns: list[str], output_format: str) -> None:
    """Render stable table, TSV, or JSON output to standard output."""
    materialized = list(rows)
    if output_format == "json":
        click.echo(json.dumps(materialized, indent=2, default=str))
        return
    if output_format == "tsv":
        click.echo("\t".join(columns))
        for row in materialized:
            click.echo("\t".join(_text(row.get(column)).replace("\t", " ") for column in columns))
        return
    widths = {
        column: max([len(column.upper()), *[len(_text(row.get(column))) for row in materialized]]) for column in columns
    }
    click.echo("  ".join(column.upper().ljust(widths[column]) for column in columns))
    for row in materialized:
        click.echo("  ".join(_text(row.get(column)).ljust(widths[column]) for column in columns))


def _catalog(name: str) -> Datacatalog:
    catalog = Datacatalog.objects(name=name).first()
    if not catalog:
        raise click.ClickException(f"Catalogue '{name}' was not found.")
    return catalog


def _snapshot(catalog: Datacatalog, name: str, include_retired: bool) -> TreeSnapshot:
    snapshot = TreeSnapshot.objects(collection=catalog, name=name).first()
    if not snapshot:
        raise click.ClickException(f"Snapshot '{name}' was not found for catalogue '{catalog.name}'.")
    if snapshot.state == "published" or (include_retired and snapshot.state == "retired"):
        return snapshot
    if snapshot.state == "retired":
        raise click.ClickException(f"Snapshot '{name}' is retired; pass --include-retired to inspect it.")
    raise click.ClickException(f"Snapshot '{name}' is not published.")


def _iso(value) -> str | None:
    return value.isoformat(timespec="seconds") if value else None


def _entry_row(entry: TreeEntry, include_detail: bool = False) -> dict[str, Any]:
    row: dict[str, Any] = {
        "path": entry.relative_path,
        "name": entry.name,
        "kind": entry.kind,
        "modality": (entry.metadata or {}).get("modality"),
        "role": (entry.metadata or {}).get("role"),
        "size": None,
    }
    if include_detail:
        row["target_path"] = entry.target_path
        row["status"] = "available"
    if entry.kind == "file":
        try:
            row["size"] = entry.dataset.size if entry.dataset else None
        except DoesNotExist:
            row["status"] = "dataset deleted"
    return row


def _human_size(value: int | None) -> str | None:
    if value is None:
        return None
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return None


def _modality_roots(entries: list[TreeEntry], modality: str) -> set[str]:
    return {
        entry.relative_path
        for entry in entries
        if (entry.metadata or {}).get("role") == "modality"
        and (entry.metadata or {}).get("modality", "").casefold() == modality.casefold()
    }


def _in_modality(path: str, roots: set[str]) -> bool:
    return any(path == root or path.startswith(f"{root}/") for root in roots)


@cloup.group("browse", help="Discover published catalogue snapshots without modifying data.")
def browse() -> None:
    pass


@browse.command("catalogs")
@cloup.option("--format", "output_format", type=OUTPUT_FORMAT, default="table", show_default=True)
def browse_catalogs(output_format: str) -> None:
    """List catalogues available for exploration."""
    with get_mec(uri=get_mongo_uri()):
        rows = [
            {
                "name": catalog.name,
                "description": catalog.description,
                "keywords": catalog.keywords or [],
                "created": _iso(catalog.date_created),
            }
            for catalog in Datacatalog.objects().order_by("name")
        ]
    _emit(rows, ["name", "description", "keywords", "created"], output_format)


@browse.command("snapshots")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.option("--include-retired", is_flag=True, help="Also show retired snapshots.")
@cloup.option("--format", "output_format", type=OUTPUT_FORMAT, default="table", show_default=True)
def browse_snapshots(collection_name: str, include_retired: bool, output_format: str) -> None:
    """List published snapshots in a catalogue."""
    with get_mec(uri=get_mongo_uri()):
        catalog = _catalog(collection_name)
        states = ["published", "retired"] if include_retired else ["published"]
        rows = [
            {
                "name": snapshot.name,
                "state": snapshot.state,
                "published": _iso(snapshot.published_at),
                "retired": _iso(snapshot.retired_at),
                "reason": snapshot.retirement_reason,
                "manifest_sha256": snapshot.manifest_sha256,
            }
            for snapshot in TreeSnapshot.objects(collection=catalog, state__in=states).order_by("-created_at")
        ]
    _emit(rows, ["name", "state", "published", "retired", "reason", "manifest_sha256"], output_format)


@browse.command("show")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
@cloup.option("--include-retired", is_flag=True, help="Allow inspection of a retired snapshot.")
@cloup.option("--format", "output_format", type=OUTPUT_FORMAT, default="table", show_default=True)
def browse_show(collection_name: str, snapshot_name: str, include_retired: bool, output_format: str) -> None:
    """Show summary, provenance, and curated modalities for one snapshot."""
    with get_mec(uri=get_mongo_uri()):
        snapshot = _snapshot(_catalog(collection_name), snapshot_name, include_retired)
        entries = list(TreeEntry.objects(snapshot=snapshot))
        modalities = sorted(
            {
                (entry.metadata or {}).get("modality")
                for entry in entries
                if (entry.metadata or {}).get("role") == "modality" and (entry.metadata or {}).get("modality")
            }
        )
        known_size = 0
        unknown_size = False
        for entry in entries:
            if entry.kind != "file":
                continue
            try:
                size = entry.dataset.size if entry.dataset else None
            except DoesNotExist:
                size = None
            if size is None:
                unknown_size = True
            else:
                known_size += size
        row = {
            "catalog": snapshot.collection.name,
            "snapshot": snapshot.name,
            "state": snapshot.state,
            "published": _iso(snapshot.published_at),
            "retired": _iso(snapshot.retired_at),
            "retirement_reason": snapshot.retirement_reason,
            "manifest_sha256": snapshot.manifest_sha256,
            "directories": sum(entry.kind == "directory" for entry in entries),
            "files": sum(entry.kind == "file" for entry in entries),
            "aliases": sum(entry.kind == "alias" for entry in entries),
            "known_size_bytes": known_size,
            "size_complete": not unknown_size,
            "modalities": modalities,
            "additional_source_count": len((snapshot.metadata or {}).get("additional_sources", [])),
        }
    if output_format == "table":
        for key, value in row.items():
            click.echo(f"{key}: {_text(value)}")
    else:
        _emit([row], list(row), output_format)


@browse.command("describe")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
@cloup.argument("path")
@cloup.option("--include-retired", is_flag=True, help="Allow inspection of a retired snapshot.")
@cloup.option("--format", "output_format", type=OUTPUT_FORMAT, default="table", show_default=True)
def browse_describe(
    collection_name: str, snapshot_name: str, path: str, include_retired: bool, output_format: str
) -> None:
    """Show detailed metadata for one logical file, directory, or alias."""
    logical_path = PurePosixPath(path)
    if logical_path.is_absolute() or logical_path == PurePosixPath(".") or ".." in logical_path.parts:
        raise click.UsageError("PATH must be a safe relative logical path.")
    normalized_path = logical_path.as_posix()
    with get_mec(uri=get_mongo_uri()):
        snapshot = _snapshot(_catalog(collection_name), snapshot_name, include_retired)
        entry = TreeEntry.objects(snapshot=snapshot, relative_path=normalized_path).first()
        if not entry:
            raise click.ClickException(f"Logical path '{normalized_path}' was not found.")
        aliases = [
            alias.relative_path
            for alias in TreeEntry.objects(snapshot=snapshot, kind="alias", target_path=normalized_path).order_by(
                "relative_path"
            )
        ]
        row: dict[str, Any] = {
            "catalog": snapshot.collection.name,
            "snapshot": snapshot.name,
            "path": entry.relative_path,
            "name": entry.name,
            "kind": entry.kind,
            "parent_path": entry.parent_path or None,
            "metadata": entry.metadata or {},
            "target_path": entry.target_path,
            "aliases": aliases,
            "dataset_id": None,
            "checksum": None,
            "size": None,
            "encoding_format": None,
            "protocol": None,
            "date_created": None,
            "date_modified": None,
            "status": "available",
        }
        if entry.kind == "file":
            try:
                dataset = entry.dataset
            except DoesNotExist:
                row["status"] = "dataset deleted"
            else:
                if dataset is None:
                    row["status"] = "dataset missing"
                else:
                    row.update(
                        {
                            "dataset_id": dataset.uk,
                            "checksum": dataset.checksum,
                            "size": dataset.size,
                            "encoding_format": dataset.encoding_format,
                            "protocol": dataset.protocol,
                            "date_created": _iso(dataset.date_created),
                            "date_modified": _iso(dataset.date_modified),
                        }
                    )
        elif entry.kind == "alias":
            target = TreeEntry.objects(snapshot=snapshot, relative_path=entry.target_path).first()
            if not target:
                row["status"] = "target missing"
    if output_format == "table":
        for key, value in row.items():
            click.echo(f"{key}: {_text(value)}")
    else:
        _emit([row], list(row), output_format)


@browse.command("ls")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
@cloup.argument("path", required=False, default="")
@cloup.option("-R", "--recursive", is_flag=True, help="List all descendants, not only immediate children.")
@cloup.option("-l", "--long", "long_format", is_flag=True, help="Include alias target and entry status columns.")
@cloup.option("-h", "--human-readable", is_flag=True, help="Render sizes as KiB, MiB, and so on in table/TSV output.")
@cloup.option(
    "--sort", "sort_by", type=click.Choice(("name", "path", "kind", "size")), default="name", show_default=True
)
@cloup.option("--reverse", is_flag=True, help="Reverse the selected sort order.")
@cloup.option("--include-retired", is_flag=True, help="Allow inspection of a retired snapshot.")
@cloup.option("--format", "output_format", type=OUTPUT_FORMAT, default="table", show_default=True)
def browse_ls(
    collection_name: str,
    snapshot_name: str,
    path: str,
    recursive: bool,
    long_format: bool,
    human_readable: bool,
    sort_by: str,
    reverse: bool,
    include_retired: bool,
    output_format: str,
) -> None:
    """List immediate logical children of PATH, or of the snapshot root."""
    requested = PurePosixPath(path) if path else PurePosixPath(".")
    requested_path = "" if requested == PurePosixPath(".") else requested.as_posix()
    if requested.is_absolute() or ".." in requested.parts:
        raise click.UsageError("PATH must be a safe relative logical path.")
    with get_mec(uri=get_mongo_uri()):
        snapshot = _snapshot(_catalog(collection_name), snapshot_name, include_retired)
        if requested_path:
            parent = TreeEntry.objects(snapshot=snapshot, relative_path=requested_path).first()
            if not parent:
                raise click.ClickException(f"Logical path '{requested_path}' was not found.")
            if parent.kind != "directory":
                raise click.ClickException(
                    f"Logical path '{requested_path}' is a {parent.kind}, not a directory. "
                    f"Use 'omnia browse describe {collection_name} {snapshot_name} {requested_path}'."
                )
        entries = list(TreeEntry.objects(snapshot=snapshot))
        if recursive:
            prefix = f"{requested_path}/" if requested_path else ""
            entries = [entry for entry in entries if not requested_path or entry.relative_path.startswith(prefix)]
        else:
            entries = [entry for entry in entries if entry.parent_path == requested_path]
        rows = [_entry_row(entry, include_detail=long_format) for entry in entries]

    sort_key = {
        "name": lambda row: row["name"].casefold(),
        "path": lambda row: row["path"],
        "kind": lambda row: (row["kind"], row["path"]),
        "size": lambda row: (row["size"] is None, row["size"] or 0, row["path"]),
    }[sort_by]
    rows.sort(key=sort_key, reverse=reverse)
    columns = ["name", "kind", "modality", "role", "size", "path"]
    if long_format:
        columns.extend(("target_path", "status"))
    if human_readable and output_format != "json":
        rows = [{**row, "size": _human_size(row["size"])} for row in rows]
    _emit(rows, columns, output_format)


@browse.command("find")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
@cloup.option("--modality", help="Restrict results to a curated modality subtree.")
@cloup.option("--name", "name_pattern", help="Filter entry names with a shell glob, such as '*.pgen'.")
@cloup.option("--path", "path_pattern", help="Filter logical paths with a shell glob, such as 'annex/**'.")
@cloup.option("--kind", type=click.Choice(("directory", "file", "alias")))
@cloup.option("--limit", type=click.IntRange(min=1), default=100, show_default=True)
@cloup.option("--offset", type=click.IntRange(min=0), default=0, show_default=True)
@cloup.option("--include-retired", is_flag=True, help="Allow inspection of a retired snapshot.")
@cloup.option("--format", "output_format", type=OUTPUT_FORMAT, default="table", show_default=True)
def browse_find(
    collection_name: str,
    snapshot_name: str,
    modality: str | None,
    name_pattern: str | None,
    path_pattern: str | None,
    kind: str | None,
    limit: int,
    offset: int,
    include_retired: bool,
    output_format: str,
) -> None:
    """Search logical paths and curator metadata in a published snapshot."""
    with get_mec(uri=get_mongo_uri()):
        snapshot = _snapshot(_catalog(collection_name), snapshot_name, include_retired)
        entries = list(TreeEntry.objects(snapshot=snapshot).order_by("relative_path"))
        if modality:
            roots = _modality_roots(entries, modality)
            if not roots:
                raise click.ClickException(f"No modality '{modality}' is defined in this snapshot.")
            entries = [entry for entry in entries if _in_modality(entry.relative_path, roots)]
        if kind:
            entries = [entry for entry in entries if entry.kind == kind]
        if name_pattern:
            entries = [entry for entry in entries if fnmatch.fnmatchcase(entry.name, name_pattern)]
        if path_pattern:
            entries = [entry for entry in entries if fnmatch.fnmatchcase(entry.relative_path, path_pattern)]
        total = len(entries)
        rows = [_entry_row(entry) for entry in entries[offset : offset + limit]]
    if output_format == "json":
        click.echo(json.dumps({"total": total, "offset": offset, "items": rows}, indent=2, default=str))
    else:
        _emit(rows, ["name", "kind", "modality", "role", "size", "path"], output_format)
        click.echo(f"{total} matching entries")

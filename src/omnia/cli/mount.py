"""The ``omnia mount`` command."""

from __future__ import annotations

import json
from pathlib import Path

import click
import cloup

from omnia.config.config_manager import get_storage_roots
from omnia.filesystem import AliasEntry, DatasetEntry, OmniaVirtualTree, PosixObjectResolver, StorageRootError
from omnia.filesystem.fuse_adapter import mount as fuse_mount
from omnia.models.data_collection import Datacatalog
from omnia.models.data_object import Dataset
from omnia.models.data_tree import TreeEntry, TreeSnapshot
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri


def _dataset_entries(
    collection_name: str | None, storage_roots: list[str]
) -> tuple[list[DatasetEntry], PosixObjectResolver]:
    """Load and validate the selected datasets before starting the FUSE loop."""
    resolver = PosixObjectResolver(storage_roots)
    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalogs = Datacatalog.objects(name=collection_name) if collection_name else Datacatalog.objects()
        catalogs = list(catalogs)
        if collection_name and not catalogs:
            raise click.UsageError(f"Catalogue '{collection_name}' was not found.")

        seen: set[str] = set()
        entries: list[DatasetEntry] = []
        for catalog in catalogs:
            for dataset in Dataset.objects(included_in_datacatalog=catalog):
                if dataset.uk in seen:
                    continue
                try:
                    resolver.register(dataset.uk, dataset.path)
                except StorageRootError as error:
                    raise click.UsageError(str(error)) from error
                seen.add(dataset.uk)
                entries.append(
                    DatasetEntry(
                        object_id=dataset.uk,
                        name=Path(dataset.path).name,
                        size=dataset.size if dataset.size is not None else resolver.size(dataset.uk),
                        modified_at=dataset.date_modified or dataset.date_created,
                    )
                )
    return entries, resolver


def _snapshot_entries(
    collection_name: str, snapshot_name: str, storage_roots: list[str]
) -> tuple[list[DatasetEntry], list[str], list[AliasEntry], PosixObjectResolver, bytes]:
    """Load one published hierarchy, preserving its logical relative paths."""
    resolver = PosixObjectResolver(storage_roots)
    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = Datacatalog.objects(name=collection_name).first()
        snapshot = TreeSnapshot.objects(collection=catalog, name=snapshot_name).first() if catalog else None
        if not snapshot:
            raise click.UsageError(f"Snapshot '{snapshot_name}' was not found for '{collection_name}'.")
        if snapshot.state == "retired":
            raise click.UsageError(f"Snapshot '{snapshot_name}' is retired and cannot be mounted.")
        if snapshot.state != "published":
            raise click.UsageError(f"Snapshot '{snapshot_name}' is not published.")

        entries: list[DatasetEntry] = []
        directories: list[str] = []
        aliases: list[AliasEntry] = []
        for tree_entry in TreeEntry.objects(snapshot=snapshot):
            if tree_entry.kind == "directory":
                directories.append(tree_entry.relative_path)
                continue
            if tree_entry.kind == "alias":
                aliases.append(AliasEntry(tree_entry.relative_path, tree_entry.target_path))
                continue
            if tree_entry.kind != "file" or tree_entry.dataset is None:
                continue
            dataset = tree_entry.dataset
            try:
                resolver.register(dataset.uk, dataset.path)
            except StorageRootError as error:
                raise click.UsageError(str(error)) from error
            entries.append(
                DatasetEntry(
                    object_id=dataset.uk,
                    name=tree_entry.name,
                    size=dataset.size if dataset.size is not None else resolver.size(dataset.uk),
                    modified_at=dataset.date_modified or dataset.date_created,
                    relative_path=tree_entry.relative_path,
                )
            )
        marker = (
            json.dumps(
                {
                    "catalog": snapshot.collection.name,
                    "snapshot": snapshot.name,
                    "snapshot_id": str(snapshot.id),
                    "manifest_sha256": snapshot.manifest_sha256,
                },
                indent=2,
            ).encode("utf-8")
            + b"\n"
        )
    return entries, directories, aliases, resolver, marker


def _mount_arguments(
    first: str,
    second: str | None,
    third: str | None,
    legacy_collection: str | None,
    legacy_snapshot: str | None,
) -> tuple[str | None, str | None, Path]:
    """Support the concise snapshot syntax and the legacy option syntax."""
    if third is not None:
        if legacy_collection or legacy_snapshot:
            raise click.UsageError("Do not combine positional snapshot arguments with --collection or --snapshot.")
        if second is None:
            raise click.UsageError("Snapshot name is required before the mount point.")
        return first, second, Path(third)
    if second is not None:
        raise click.UsageError("Use 'omnia mount CATALOGUE SNAPSHOT MOUNTPOINT' for a snapshot mount.")
    return legacy_collection, legacy_snapshot, Path(first)


def _configured_or_explicit_roots(
    collection_name: str | None, storage_roots: tuple[Path, ...], storage_profile: str | None
) -> list[str]:
    if storage_roots:
        if storage_profile:
            raise click.UsageError("Use either --storage-root or --storage-profile, not both.")
        return [str(root) for root in storage_roots]
    if not collection_name:
        raise click.UsageError("A catalogue is required when Omnia resolves a configured storage profile.")
    try:
        return get_storage_roots(collection_name, storage_profile)
    except ValueError as error:
        raise click.UsageError(str(error)) from error


@cloup.command(
    "mount",
    no_args_is_help=True,
    help="Mount a read-only snapshot: `omnia mount CATALOGUE SNAPSHOT MOUNTPOINT`.",
)
@cloup.argument("first", metavar="CATALOGUE")
@cloup.argument("second", required=False, metavar="SNAPSHOT")
@cloup.argument("third", required=False, metavar="MOUNTPOINT")
@cloup.option("--collection", "legacy_collection", help="Legacy: expose only datasets in this catalogue.")
@cloup.option(
    "--snapshot", "legacy_snapshot", help="Legacy: expose this published tree snapshot; requires --collection."
)
@cloup.option(
    "--storage-root",
    "storage_roots",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=Path),
    multiple=True,
    help="Advanced override: trusted root containing registered data. Repeat for multiple roots.",
)
@cloup.option("--storage-profile", help="Configured trusted storage profile. Defaults to default_storage_profile.")
@cloup.option("--foreground/--background", default=True, help="Keep the FUSE process attached to this terminal.")
def mount_datasets(
    first: str,
    second: str | None,
    third: str | None,
    legacy_collection: str | None,
    legacy_snapshot: str | None,
    storage_roots: tuple[Path, ...],
    storage_profile: str | None,
    foreground: bool,
) -> None:
    """Mount an Omnia catalogue view at MOUNTPOINT.

    The command only reads files that are registered in Omnia and located
    below configured or explicitly supplied trusted storage roots.
    """
    collection_name, snapshot_name, mountpoint = _mount_arguments(
        first, second, third, legacy_collection, legacy_snapshot
    )
    if not mountpoint.is_dir():
        raise click.UsageError(f"Mount point must be an existing directory: {mountpoint}")
    if any(mountpoint.iterdir()):
        raise click.UsageError(f"Mount point must be empty: {mountpoint}")
    if snapshot_name and not collection_name:
        raise click.UsageError("--snapshot requires --collection.")
    roots = _configured_or_explicit_roots(collection_name, storage_roots, storage_profile)
    if snapshot_name:
        entries, directories, aliases, resolver, marker = _snapshot_entries(collection_name, snapshot_name, roots)
    else:
        entries, resolver = _dataset_entries(collection_name, roots)
        directories = []
        aliases = []
        marker = None
    if not entries:
        raise click.UsageError("No registered datasets are available for this mount.")
    metadata_files = {".omnia-snapshot.json": marker} if marker else None
    tree = OmniaVirtualTree(entries, directories=directories, aliases=aliases, metadata_files=metadata_files)
    fuse_mount(tree, resolver, str(mountpoint), foreground=foreground)

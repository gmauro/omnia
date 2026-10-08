"""Commands for ingesting and publishing versioned catalogue trees."""

from __future__ import annotations

import datetime
import os
from copy import deepcopy
from pathlib import Path, PurePosixPath

import click
import cloup
from mongoengine.errors import DoesNotExist, ValidationError

from omnia.cli.commons import get_datacatalog
from omnia.config.config_manager import get_storage_roots
from omnia.models.data_object import Dataset, PosixDataObject
from omnia.models.data_tree import TreeEntry, TreeSnapshot
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri
from omnia.tree_export import ExportError, export_links
from omnia.tree_manifest import CuratorManifest, ManifestError, apply_manifest, load_manifest, retarget_manifest


def _logical_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _entry_parts(relative_path: str) -> tuple[str, str]:
    logical = PurePosixPath(relative_path)
    return logical.parent.as_posix() if logical.parent != PurePosixPath(".") else "", logical.name


def _add_entry(snapshot, relative_path: str, kind: str, dataset=None, target_path: str | None = None) -> None:
    parent_path, name = _entry_parts(relative_path)
    TreeEntry(
        snapshot=snapshot,
        relative_path=relative_path,
        parent_path=parent_path,
        name=name,
        kind=kind,
        dataset=dataset,
        target_path=target_path,
    ).save()


def _add_entry_with_parents(
    snapshot: TreeSnapshot,
    relative_path: str,
    kind: str,
    logical_paths: set[str],
    dataset=None,
    target_path: str | None = None,
) -> int:
    """Add a logical entry and any synthetic directories required by a rename."""
    if relative_path in logical_paths:
        raise ManifestError(f"Logical path collision after manifest rename: {relative_path}")
    added_directories = 0
    parent = PurePosixPath(relative_path).parent
    missing_parents: list[str] = []
    while parent != PurePosixPath("."):
        parent_path = parent.as_posix()
        if parent_path not in logical_paths:
            missing_parents.append(parent_path)
        parent = parent.parent
    for parent_path in reversed(missing_parents):
        _add_entry(snapshot, parent_path, "directory")
        logical_paths.add(parent_path)
        added_directories += 1
    _add_entry(snapshot, relative_path, kind, dataset=dataset, target_path=target_path)
    logical_paths.add(relative_path)
    return added_directories


def _record_file(path: Path, catalog, compute_metadata: bool) -> Dataset:
    dataset = Dataset.objects(path=str(path)).first()
    if dataset:
        if catalog not in dataset.included_in_datacatalog:
            dataset.included_in_datacatalog.append(catalog)
            dataset.save()
        return dataset

    object_wrapper = PosixDataObject(path=str(path), included_in_datacatalog=[catalog])
    if compute_metadata:
        object_wrapper.compute()
    object_wrapper.save()
    # Dataset.uk is currently unique across matching content/name pairs.  The
    # wrapper may therefore have encountered an existing object and remain
    # unsaved; always resolve the persisted canonical document before using it
    # as a TreeEntry reference.
    dataset = Dataset.objects(uk=object_wrapper.mdb_obj.uk).first()
    if dataset is None:
        raise ValidationError(f"Could not persist or resolve dataset: {path}")
    if catalog not in dataset.included_in_datacatalog:
        dataset.included_in_datacatalog.append(catalog)
        dataset.save()
    return dataset


def _remove_snapshot(snapshot: TreeSnapshot) -> None:
    """Remove a draft and all of its entries, including partial ingestions."""
    TreeEntry.objects(snapshot=snapshot).delete()
    snapshot.delete()


def _validate(snapshot: TreeSnapshot) -> list[str]:
    entries = list(TreeEntry.objects(snapshot=snapshot))
    paths = {entry.relative_path for entry in entries}
    errors: list[str] = []
    for entry in entries:
        if entry.parent_path and entry.parent_path not in paths:
            errors.append(f"{entry.relative_path}: missing parent {entry.parent_path}")
        if entry.kind == "file":
            try:
                dataset = entry.dataset
            except DoesNotExist:
                errors.append(f"{entry.relative_path}: referenced dataset was deleted")
            else:
                if dataset is None:
                    errors.append(f"{entry.relative_path}: file entry has no dataset")
        if entry.kind == "alias" and (not entry.target_path or entry.target_path not in paths):
            errors.append(f"{entry.relative_path}: alias target is missing")
    return errors


def _manifest_for_ingestion(
    manifest_path: Path | None, collection_name: str, snapshot_name: str
) -> CuratorManifest | None:
    if manifest_path is None:
        return None
    manifest = load_manifest(manifest_path)
    if manifest.catalog and manifest.catalog != collection_name:
        raise ManifestError(f"Manifest catalog is '{manifest.catalog}', expected '{collection_name}'")
    if manifest.snapshot and manifest.snapshot != snapshot_name:
        raise ManifestError(f"Manifest snapshot is '{manifest.snapshot}', expected '{snapshot_name}'")
    return manifest


def _safe_logical_path(value: str) -> str:
    """Return a safe, non-empty path relative to the snapshot root."""
    path = PurePosixPath(value)
    if not value or path.is_absolute() or any(part == ".." for part in path.parts):
        raise ValueError("Destination must be a non-empty safe relative path")
    normalized = path.as_posix()
    if normalized in ("", "."):
        raise ValueError("Destination must be a non-empty safe relative path")
    return normalized


def _path_below(root: Path, path: Path) -> str:
    """Map PATH to a logical path below ROOT, rejecting external aliases."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError as error:
        raise ValueError(f"Symbolic link points outside the added source: {path}") from error


def _addition_plan(source: Path, destination: str) -> list[tuple[str, str, Path | str | None]]:
    """Describe entries required to add SOURCE at DESTINATION to a snapshot."""
    destination = _safe_logical_path(destination)
    if source.is_file():
        return [(destination, "file", source)]

    plan: list[tuple[str, str, Path | str | None]] = [(destination, "directory", None)]
    for current_root, directories, filenames in os.walk(source, followlinks=False):
        current = Path(current_root)
        relative_root = current.relative_to(source)
        retained_directories = []
        for directory in directories:
            path = current / directory
            logical_path = (PurePosixPath(destination) / relative_root / directory).as_posix()
            if path.is_symlink():
                target = _path_below(source, path.resolve(strict=True))
                target_path = (PurePosixPath(destination) / target).as_posix()
                plan.append((logical_path, "alias", target_path))
            else:
                plan.append((logical_path, "directory", None))
                retained_directories.append(directory)
        directories[:] = retained_directories

        for filename in filenames:
            path = current / filename
            logical_path = (PurePosixPath(destination) / relative_root / filename).as_posix()
            if path.is_symlink():
                target = _path_below(source, path.resolve(strict=True))
                target_path = (PurePosixPath(destination) / target).as_posix()
                plan.append((logical_path, "alias", target_path))
            else:
                plan.append((logical_path, "file", path))
    return plan


def _with_missing_parents(
    snapshot: TreeSnapshot, plan: list[tuple[str, str, Path | str | None]]
) -> list[tuple[str, str, Path | str | None]]:
    """Add missing logical parent directories and reject all path collisions."""
    existing = {entry.relative_path: entry.kind for entry in TreeEntry.objects(snapshot=snapshot)}
    return _with_missing_parents_from_existing(existing, plan)


def _with_missing_parents_from_existing(
    existing: dict[str, str], plan: list[tuple[str, str, Path | str | None]]
) -> list[tuple[str, str, Path | str | None]]:
    """Add missing parents to PLAN, given a map of paths that will remain."""
    planned = {path for path, _, _ in plan}
    collisions = sorted(planned.intersection(existing))
    if collisions:
        raise ValueError(f"Logical path already exists: {collisions[0]}")

    parents: set[str] = set()
    for path in planned:
        parent = PurePosixPath(path).parent
        while parent != PurePosixPath("."):
            parent_path = parent.as_posix()
            existing_kind = existing.get(parent_path)
            if existing_kind and existing_kind != "directory":
                raise ValueError(f"Logical parent is not a directory: {parent_path}")
            if parent_path not in existing and parent_path not in planned:
                parents.add(parent_path)
            parent = parent.parent
    parent_entries = [(path, "directory", None) for path in sorted(parents, key=lambda item: (item.count("/"), item))]
    return parent_entries + plan


def _copy_entry(entry: TreeEntry, snapshot: TreeSnapshot) -> None:
    """Copy a logical entry while preserving its Dataset reference and metadata."""
    TreeEntry(
        snapshot=snapshot,
        relative_path=entry.relative_path,
        parent_path=entry.parent_path,
        name=entry.name,
        kind=entry.kind,
        dataset=entry.dataset,
        target_path=entry.target_path,
        metadata=deepcopy(entry.metadata),
    ).save()


def _is_in_subtree(relative_path: str, root: str) -> bool:
    return relative_path == root or relative_path.startswith(f"{root}/")


@cloup.group("tree", help="Ingest, validate, and publish hierarchical catalogue snapshots.")
def tree():
    pass


@tree.command("ingest")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("source", type=click.Path(exists=True, file_okay=False, path_type=Path))
@cloup.argument("snapshot_name")
@cloup.option("-k", "--skip-metadata-computation", is_flag=True, help="Do not calculate file checksums and MIME types.")
@cloup.option("--manifest", "manifest_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def ingest_tree(
    collection_name: str,
    source: Path,
    snapshot_name: str,
    skip_metadata_computation: bool,
    manifest_path: Path | None,
) -> None:
    """Register SOURCE and create a draft logical tree snapshot."""
    source = source.resolve(strict=True)
    try:
        manifest = _manifest_for_ingestion(manifest_path, collection_name, snapshot_name)
    except ManifestError as error:
        raise click.UsageError(str(error)) from error
    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = get_datacatalog(collection_name)
        if not catalog:
            raise click.UsageError(f"Catalogue '{collection_name}' was not found.")
        if TreeSnapshot.objects(collection=catalog, name=snapshot_name).first():
            raise click.UsageError(f"Snapshot '{snapshot_name}' already exists for '{collection_name}'.")

        snapshot = TreeSnapshot(collection=catalog, name=snapshot_name, source_root=str(source)).save()
        count = {"directories": 0, "files": 0, "aliases": 0}
        logical_paths: set[str] = set()
        try:
            for current_root, directories, filenames in os.walk(source, followlinks=False):
                current = Path(current_root)
                retained_directories = []
                for directory in directories:
                    path = current / directory
                    source_relative_path = _logical_path(source, path)
                    if manifest and manifest.excludes(source_relative_path):
                        continue
                    relative_path = manifest.logical_path(source_relative_path) if manifest else source_relative_path
                    if path.is_symlink():
                        target = path.resolve(strict=True)
                        target_source_path = _logical_path(source, target)
                        target_path = manifest.logical_path(target_source_path) if manifest else target_source_path
                        count["directories"] += _add_entry_with_parents(
                            snapshot, relative_path, "alias", logical_paths, target_path=target_path
                        )
                        count["aliases"] += 1
                    else:
                        count["directories"] += _add_entry_with_parents(
                            snapshot, relative_path, "directory", logical_paths
                        )
                        retained_directories.append(directory)
                        count["directories"] += 1
                directories[:] = retained_directories

                for filename in filenames:
                    path = current / filename
                    source_relative_path = _logical_path(source, path)
                    if manifest and manifest.excludes(source_relative_path):
                        continue
                    relative_path = manifest.logical_path(source_relative_path) if manifest else source_relative_path
                    if path.is_symlink():
                        target = path.resolve(strict=True)
                        target_source_path = _logical_path(source, target)
                        target_path = manifest.logical_path(target_source_path) if manifest else target_source_path
                        count["directories"] += _add_entry_with_parents(
                            snapshot, relative_path, "alias", logical_paths, target_path=target_path
                        )
                        count["aliases"] += 1
                        continue
                    dataset = _record_file(path, catalog, not skip_metadata_computation)
                    count["directories"] += _add_entry_with_parents(
                        snapshot, relative_path, "file", logical_paths, dataset=dataset
                    )
                    count["files"] += 1
        except (OSError, ValueError, ValidationError, ManifestError) as error:
            _remove_snapshot(snapshot)
            raise click.ClickException(f"Ingestion aborted; draft snapshot was removed: {error}") from error

        try:
            if manifest:
                apply_manifest(snapshot, manifest)
        except ManifestError as error:
            _remove_snapshot(snapshot)
            raise click.ClickException(f"Ingestion validation failed; draft snapshot was removed: {error}") from error
        errors = _validate(snapshot)
        if errors:
            _remove_snapshot(snapshot)
            message = "Ingestion validation failed; draft snapshot was removed:\n" + "\n".join(errors[:20])
            raise click.ClickException(message)
    click.echo(
        f"Draft snapshot '{snapshot_name}' created: {count['directories']} directories, "
        f"{count['files']} files, {count['aliases']} aliases."
    )


@tree.command("clone")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("source_snapshot_name")
@cloup.argument("target_snapshot_name")
def clone_tree(collection_name: str, source_snapshot_name: str, target_snapshot_name: str) -> None:
    """Clone a published snapshot into a new draft without copying data bytes."""
    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = get_datacatalog(collection_name)
        source = TreeSnapshot.objects(collection=catalog, name=source_snapshot_name).first() if catalog else None
        if not source:
            raise click.UsageError("Source snapshot was not found.")
        if source.state != "published":
            raise click.UsageError("Only published snapshots can be cloned.")
        if TreeSnapshot.objects(collection=catalog, name=target_snapshot_name).first():
            raise click.UsageError(f"Snapshot '{target_snapshot_name}' already exists for '{collection_name}'.")

        metadata = deepcopy(source.metadata or {})
        metadata["cloned_from"] = {
            "snapshot": source.name,
            "snapshot_id": str(source.id),
            "manifest_sha256": source.manifest_sha256,
        }
        manifest_content = source.manifest_content
        manifest_sha256 = source.manifest_sha256
        if manifest_content:
            try:
                manifest_content, manifest_sha256 = retarget_manifest(manifest_content, target_snapshot_name)
            except ManifestError as error:
                raise click.ClickException(f"Could not retarget the source manifest: {error}") from error
        target = TreeSnapshot(
            collection=catalog,
            name=target_snapshot_name,
            source_root=source.source_root,
            state="draft",
            metadata=metadata,
            manifest_content=manifest_content,
            manifest_sha256=manifest_sha256,
        ).save()
        try:
            for entry in TreeEntry.objects(snapshot=source):
                _copy_entry(entry, target)
        except Exception as error:
            _remove_snapshot(target)
            raise click.ClickException(f"Snapshot clone aborted; draft was removed: {error}") from error
    click.echo(f"Draft snapshot '{target_snapshot_name}' cloned from '{source_snapshot_name}'.")


@tree.command("replace-path")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
@cloup.argument("source", type=click.Path(exists=True, path_type=Path))
@cloup.argument("destination")
@cloup.option("-k", "--skip-metadata-computation", is_flag=True, help="Do not calculate file checksums and MIME types.")
@cloup.option("--manifest", "manifest_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def replace_tree_path(
    collection_name: str,
    snapshot_name: str,
    source: Path,
    destination: str,
    skip_metadata_computation: bool,
    manifest_path: Path | None,
) -> None:
    """Replace one logical subtree in a draft snapshot with SOURCE."""
    source = source.resolve(strict=True)
    try:
        plan = _addition_plan(source, destination)
        manifest = _manifest_for_ingestion(manifest_path, collection_name, snapshot_name)
    except (OSError, ValueError, ManifestError) as error:
        raise click.UsageError(str(error)) from error

    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = get_datacatalog(collection_name)
        snapshot = TreeSnapshot.objects(collection=catalog, name=snapshot_name).first() if catalog else None
        if not snapshot:
            raise click.UsageError("Snapshot was not found.")
        if snapshot.state != "draft":
            raise click.UsageError(f"Paths can only be replaced in draft snapshots (current state: {snapshot.state}).")

        destination = _safe_logical_path(destination)
        existing_entries = list(TreeEntry.objects(snapshot=snapshot))
        removed_entries = [entry for entry in existing_entries if _is_in_subtree(entry.relative_path, destination)]
        if not removed_entries:
            raise click.UsageError(f"Logical path '{destination}' does not exist; use 'omnia tree add-path' instead.")
        remaining = {
            entry.relative_path: entry.kind
            for entry in existing_entries
            if not _is_in_subtree(entry.relative_path, destination)
        }
        try:
            plan = _with_missing_parents_from_existing(remaining, plan)
        except ValueError as error:
            raise click.UsageError(str(error)) from error

        future_paths = set(remaining) | {relative_path for relative_path, _, _ in plan}
        if manifest:
            missing_nodes = [node.path for node in manifest.nodes if node.path not in future_paths]
            if missing_nodes:
                raise click.UsageError(f"Manifest node does not exist after replacement: {missing_nodes[0]}")

        prepared_plan: list[tuple[str, str, Dataset | str | None]] = []
        try:
            for relative_path, kind, value in plan:
                if kind == "file":
                    prepared_plan.append(
                        (relative_path, kind, _record_file(value, catalog, not skip_metadata_computation))
                    )
                else:
                    prepared_plan.append((relative_path, kind, value))
        except (OSError, ValidationError, ValueError) as error:
            raise click.ClickException(f"Replacement preparation failed: {error}") from error

        replaced_root = next((entry for entry in removed_entries if entry.relative_path == destination), None)
        root_metadata = deepcopy(replaced_root.metadata) if replaced_root else None
        removed_paths = [entry.relative_path for entry in removed_entries]
        TreeEntry.objects(snapshot=snapshot, relative_path__in=removed_paths).delete()
        added_paths: list[str] = []
        try:
            for relative_path, kind, value in prepared_plan:
                if kind == "file":
                    _add_entry(snapshot, relative_path, kind, dataset=value)
                elif kind == "alias":
                    _add_entry(snapshot, relative_path, kind, target_path=value)
                else:
                    _add_entry(snapshot, relative_path, kind)
                added_paths.append(relative_path)

            if root_metadata is not None:
                replacement_root = TreeEntry.objects(snapshot=snapshot, relative_path=destination).first()
                if replacement_root:
                    replacement_root.metadata = root_metadata
                    replacement_root.save()
            errors = _validate(snapshot)
            if errors:
                raise ValidationError("; ".join(errors[:20]))
            if manifest:
                apply_manifest(snapshot, manifest)
            metadata = dict(snapshot.metadata or {})
            replacements = list(metadata.get("replacements", []))
            replacements.append(
                {
                    "source": str(source),
                    "destination": destination,
                    "replaced_at": datetime.datetime.now().isoformat(timespec="seconds"),
                }
            )
            metadata["replacements"] = replacements
            if not manifest:
                if snapshot.manifest_sha256:
                    metadata["manifest_invalidated_by_replace"] = True
                    metadata["manifest_origin_sha256"] = snapshot.manifest_sha256
                snapshot.manifest_content = None
                snapshot.manifest_sha256 = None
            snapshot.metadata = metadata
            snapshot.save()
        except Exception as error:
            TreeEntry.objects(snapshot=snapshot, relative_path__in=added_paths).delete()
            for entry in removed_entries:
                _copy_entry(entry, snapshot)
            message = f"Path replacement aborted; original tree entries were restored: {error}"
            raise click.ClickException(message) from error
    click.echo(f"Replaced logical path '{destination}' in draft snapshot '{snapshot_name}'.")


@tree.command("add-path")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
@cloup.argument("source", type=click.Path(exists=True, path_type=Path))
@cloup.argument("destination")
@cloup.option("-k", "--skip-metadata-computation", is_flag=True, help="Do not calculate file checksums and MIME types.")
def add_tree_path(
    collection_name: str,
    snapshot_name: str,
    source: Path,
    destination: str,
    skip_metadata_computation: bool,
) -> None:
    """Add SOURCE below DESTINATION in a draft snapshot's logical tree.

    If SOURCE is a directory, its contents are added below DESTINATION.  If it
    is a file, DESTINATION is the file's exact logical path.
    """
    source = source.resolve(strict=True)
    try:
        plan = _addition_plan(source, destination)
    except (OSError, ValueError) as error:
        raise click.UsageError(str(error)) from error

    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = get_datacatalog(collection_name)
        snapshot = TreeSnapshot.objects(collection=catalog, name=snapshot_name).first() if catalog else None
        if not snapshot:
            raise click.UsageError("Snapshot was not found.")
        if snapshot.state != "draft":
            raise click.UsageError(f"Paths can only be added to draft snapshots (current state: {snapshot.state}).")
        try:
            plan = _with_missing_parents(snapshot, plan)
        except ValueError as error:
            raise click.UsageError(str(error)) from error

        added_paths: list[str] = []
        counts = {"directories": 0, "files": 0, "aliases": 0}
        try:
            for relative_path, kind, value in plan:
                if kind == "file":
                    dataset = _record_file(value, catalog, not skip_metadata_computation)
                    _add_entry(snapshot, relative_path, kind, dataset=dataset)
                elif kind == "alias":
                    _add_entry(snapshot, relative_path, kind, target_path=value)
                else:
                    _add_entry(snapshot, relative_path, kind)
                added_paths.append(relative_path)
                count_key = {"directory": "directories", "file": "files", "alias": "aliases"}[kind]
                counts[count_key] += 1
        except (OSError, ValidationError, ValueError) as error:
            TreeEntry.objects(snapshot=snapshot, relative_path__in=added_paths).delete()
            raise click.ClickException(f"Path addition aborted; added tree entries were removed: {error}") from error

        errors = _validate(snapshot)
        if errors:
            TreeEntry.objects(snapshot=snapshot, relative_path__in=added_paths).delete()
            message = "Path addition validation failed; added tree entries were removed:\n" + "\n".join(errors[:20])
            raise click.ClickException(message)
        metadata = dict(snapshot.metadata or {})
        additional_sources = list(metadata.get("additional_sources", []))
        additional_sources.append({"source": str(source), "destination": destination})
        metadata["additional_sources"] = additional_sources
        snapshot.metadata = metadata
        snapshot.save()
    click.echo(
        f"Added path to draft snapshot '{snapshot_name}': {counts['directories']} directories, "
        f"{counts['files']} files, {counts['aliases']} aliases."
    )


@tree.command("validate")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
def validate_tree(collection_name: str, snapshot_name: str) -> None:
    """Validate logical parents, files, and aliases in a draft snapshot."""
    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = get_datacatalog(collection_name)
        snapshot = TreeSnapshot.objects(collection=catalog, name=snapshot_name).first() if catalog else None
        if not snapshot:
            raise click.UsageError("Snapshot was not found.")
        errors = _validate(snapshot)
    if errors:
        raise click.ClickException("Validation failed:\n" + "\n".join(errors[:20]))
    click.echo(f"Snapshot '{snapshot_name}' is valid.")


@tree.command("list")
@cloup.argument("collection_name", metavar="CATALOGUE")
def list_tree_snapshots(collection_name: str) -> None:
    """List snapshots associated with a catalogue."""
    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = get_datacatalog(collection_name)
        if not catalog:
            raise click.UsageError(f"Catalogue '{collection_name}' was not found.")
        snapshots = list(TreeSnapshot.objects(collection=catalog).order_by("-created_at"))
        if not snapshots:
            click.echo(f"No snapshots found for '{collection_name}'.")
            return
        click.echo("NAME\tSTATE\tCREATED\tPUBLISHED\tRETIRED\tRETIREMENT REASON\tMANIFEST SHA-256")
        for snapshot in snapshots:
            created = snapshot.created_at.isoformat(timespec="seconds") if snapshot.created_at else "-"
            published = snapshot.published_at.isoformat(timespec="seconds") if snapshot.published_at else "-"
            retired = snapshot.retired_at.isoformat(timespec="seconds") if snapshot.retired_at else "-"
            click.echo(
                f"{snapshot.name}\t{snapshot.state}\t{created}\t{published}\t{retired}\t"
                f"{snapshot.retirement_reason or '-'}\t{snapshot.manifest_sha256 or '-'}"
            )


@tree.command("publish")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
def publish_tree(collection_name: str, snapshot_name: str) -> None:
    """Publish a validated draft snapshot for mounting and export."""
    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = get_datacatalog(collection_name)
        snapshot = TreeSnapshot.objects(collection=catalog, name=snapshot_name).first() if catalog else None
        if not snapshot:
            raise click.UsageError("Snapshot was not found.")
        if snapshot.state != "draft":
            raise click.UsageError(f"Only draft snapshots can be published (current state: {snapshot.state}).")
        errors = _validate(snapshot)
        if errors:
            raise click.ClickException("Validation failed:\n" + "\n".join(errors[:20]))
        snapshot.state = "published"
        snapshot.published_at = datetime.datetime.now()
        snapshot.save()
    click.echo(f"Snapshot '{snapshot_name}' published.")


@tree.command("retire")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
@cloup.option("--reason", help="Why this published snapshot is being retired.")
def retire_tree(collection_name: str, snapshot_name: str, reason: str | None) -> None:
    """Retire a published snapshot while retaining its provenance record."""
    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = get_datacatalog(collection_name)
        snapshot = TreeSnapshot.objects(collection=catalog, name=snapshot_name).first() if catalog else None
        if not snapshot:
            raise click.UsageError("Snapshot was not found.")
        if snapshot.state != "published":
            raise click.UsageError(f"Only published snapshots can be retired (current state: {snapshot.state}).")
        snapshot.state = "retired"
        snapshot.retired_at = datetime.datetime.now()
        snapshot.retirement_reason = reason
        snapshot.save()
    click.echo(f"Snapshot '{snapshot_name}' retired.")


@tree.command("discard")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
@cloup.option("--yes", is_flag=True, help="Confirm removal of the draft snapshot and all of its entries.")
def discard_tree(collection_name: str, snapshot_name: str, yes: bool) -> None:
    """Discard a failed or no-longer-needed draft snapshot."""
    if not yes:
        raise click.UsageError("Refusing to discard without --yes.")
    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = get_datacatalog(collection_name)
        snapshot = TreeSnapshot.objects(collection=catalog, name=snapshot_name).first() if catalog else None
        if not snapshot:
            raise click.UsageError("Snapshot was not found.")
        if snapshot.state != "draft":
            raise click.UsageError("Only draft snapshots can be discarded.")
        _remove_snapshot(snapshot)
    click.echo(f"Draft snapshot '{snapshot_name}' discarded.")


@cloup.command("export-links", help="Materialize a published tree snapshot as a read-only symlink directory.")
@cloup.argument("collection_name", metavar="CATALOGUE")
@cloup.argument("snapshot_name")
@cloup.argument("destination", type=click.Path(path_type=Path))
@cloup.option(
    "--storage-root",
    "storage_roots",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=Path),
    multiple=True,
    help="Advanced override: trusted root containing registered data. Repeat for multiple roots.",
)
@cloup.option("--storage-profile", help="Configured trusted storage profile. Defaults to default_storage_profile.")
@cloup.option("--modality", help="Export only the subtree curated with this modality.")
def export_tree_links(
    collection_name: str,
    snapshot_name: str,
    destination: Path,
    storage_roots: tuple[Path, ...],
    storage_profile: str | None,
    modality: str | None,
) -> None:
    """Export a published snapshot without copying its underlying data files."""
    if storage_roots and storage_profile:
        raise click.UsageError("Use either --storage-root or --storage-profile, not both.")
    try:
        roots = [str(root) for root in storage_roots] or get_storage_roots(collection_name, storage_profile)
    except ValueError as error:
        raise click.UsageError(str(error)) from error
    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        catalog = get_datacatalog(collection_name)
        snapshot = TreeSnapshot.objects(collection=catalog, name=snapshot_name).first() if catalog else None
        if not snapshot:
            raise click.UsageError("Snapshot was not found.")
        try:
            export_links(snapshot, destination, roots, modality=modality)
        except (ExportError, OSError, ValueError) as error:
            raise click.ClickException(str(error)) from error
    click.echo(f"Published snapshot '{snapshot_name}' exported to {destination}.")

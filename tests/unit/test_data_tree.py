import importlib
import os
import stat
from contextlib import nullcontext

import mongomock
import pytest
from click.testing import CliRunner
from mongoengine import connect, disconnect

from omnia.cli.tree import _record_file, _validate, tree
from omnia.models.data_collection import Datacatalog
from omnia.models.data_object import Dataset
from omnia.models.data_tree import TreeEntry, TreeSnapshot
from omnia.tree_export import export_links
from omnia.tree_manifest import CuratedNode, CuratorManifest, ManifestError, apply_manifest, load_manifest


def setup_function():
    disconnect()
    connect("omnia_tree_test", host="mongodb://localhost", mongo_client_class=mongomock.MongoClient)


def teardown_function():
    disconnect()


def test_tree_snapshot_validates_files_parents_and_logical_aliases():
    catalog = Datacatalog(uk="catalog-1", name="believe").save()
    dataset = Dataset(uk="dataset-1", path="/project/believe/chr1.pgen", size=10).save()
    snapshot = TreeSnapshot(collection=catalog, name="freeze-two", source_root="/project/believe").save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="genotypes",
        parent_path="",
        name="genotypes",
        kind="directory",
    ).save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="genotypes/chr1.pgen",
        parent_path="genotypes",
        name="chr1.pgen",
        kind="file",
        dataset=dataset,
    ).save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="genotypes/latest.pgen",
        parent_path="genotypes",
        name="latest.pgen",
        kind="alias",
        target_path="genotypes/chr1.pgen",
    ).save()

    assert _validate(snapshot) == []

    manifest = CuratorManifest(
        content="catalog: believe\n",
        checksum="test-checksum",
        catalog="believe",
        snapshot="freeze-two",
        nodes=(CuratedNode("genotypes", "modality", {"modality": "genotype"}),),
        exclude=("**/*.log",),
    )
    apply_manifest(snapshot, manifest)
    assert TreeEntry.objects(snapshot=snapshot, relative_path="genotypes").first().metadata == {
        "modality": "genotype",
        "role": "modality",
    }
    assert TreeSnapshot.objects(id=snapshot.id).first().manifest_sha256 == "test-checksum"

    TreeEntry(
        snapshot=snapshot,
        relative_path="broken-link",
        parent_path="",
        name="broken-link",
        kind="alias",
        target_path="missing",
    ).save()

    assert _validate(snapshot) == ["broken-link: alias target is missing"]


def test_tree_validation_reports_a_deleted_dataset_reference():
    catalog = Datacatalog(uk="catalog-dangling", name="believe-dangling").save()
    dataset = Dataset(uk="dataset-dangling", path="/project/believe/deleted.txt").save()
    snapshot = TreeSnapshot(collection=catalog, name="dangling", source_root="/project/believe").save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="deleted.txt",
        parent_path="",
        name="deleted.txt",
        kind="file",
        dataset=dataset,
    ).save()
    dataset.delete()

    assert _validate(snapshot) == ["deleted.txt: referenced dataset was deleted"]


def test_manifest_loader_validates_safe_paths_and_exclusion_patterns(tmp_path):
    manifest_path = tmp_path / "believe.yaml"
    manifest_path.write_text(
        """catalog: believe
snapshot: freeze-two
exclude:
  - '**/*.log'
nodes:
  - path: genotypes/freeze-two
    role: data_release
    metadata:
      release: Freeze Two
"""
    )

    manifest = load_manifest(manifest_path)
    assert manifest.excludes("chr1.log")
    assert manifest.excludes("genotypes/chr1.log")
    assert not manifest.excludes("genotypes/chr1.pgen")
    assert manifest.nodes[0].path == "genotypes/freeze-two"

    manifest_path.write_text("nodes:\n  - path: ../private\n")
    with pytest.raises(ManifestError, match="safe relative path"):
        load_manifest(manifest_path)


def test_manifest_loader_maps_physical_paths_to_curated_logical_paths(tmp_path):
    manifest_path = tmp_path / "renames.yaml"
    manifest_path.write_text(
        """renames:
  - source: raw_data
    destination: phenotypes/source
  - source: raw_data/qc
    destination: phenotypes/qced/qc_v2
"""
    )

    manifest = load_manifest(manifest_path)

    assert manifest.logical_path("raw_data/sample.csv") == "phenotypes/source/sample.csv"
    assert manifest.logical_path("raw_data/qc/report.html") == "phenotypes/qced/qc_v2/report.html"
    assert manifest.logical_path("annex/readme.txt") == "annex/readme.txt"


def test_tree_ingest_applies_manifest_renames_without_moving_physical_data(tmp_path, monkeypatch):
    source = tmp_path / "physical-source"
    (source / "raw_data").mkdir(parents=True)
    (source / "raw_data" / "sample.csv").write_text("sample")
    (source / "raw_data" / "current.csv").symlink_to("sample.csv")
    manifest_path = tmp_path / "renames.yaml"
    manifest_path.write_text(
        """catalog: believe-rename
snapshot: logical-v1
renames:
  - source: raw_data
    destination: phenotypes/source
nodes:
  - path: phenotypes
    role: modality
    metadata:
      modality: phenotype
"""
    )
    catalog = Datacatalog(uk="catalog-rename", name="believe-rename").save()
    tree_module = importlib.import_module("omnia.cli.tree")
    monkeypatch.setattr(tree_module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(tree_module, "get_mongo_uri", lambda: "mongodb://unused")
    monkeypatch.setattr(tree_module, "get_datacatalog", lambda name: catalog)

    result = CliRunner().invoke(
        tree,
        [
            "ingest",
            "believe-rename",
            str(source),
            "logical-v1",
            "--manifest",
            str(manifest_path),
            "--skip-metadata-computation",
        ],
    )

    snapshot = TreeSnapshot.objects(collection=catalog, name="logical-v1").first()
    assert result.exit_code == 0, result.output
    assert TreeEntry.objects(snapshot=snapshot, relative_path="phenotypes/source/sample.csv").first()
    alias = TreeEntry.objects(snapshot=snapshot, relative_path="phenotypes/source/current.csv").first()
    assert alias.kind == "alias"
    assert alias.target_path == "phenotypes/source/sample.csv"
    assert not TreeEntry.objects(snapshot=snapshot, relative_path="raw_data/sample.csv").first()
    assert TreeEntry.objects(snapshot=snapshot, relative_path="phenotypes").first().metadata["modality"] == "phenotype"
    assert snapshot.metadata["manifest_renames"] == 1


def test_tree_ingestion_resolves_the_saved_dataset_after_a_unique_key_collision(tmp_path):
    catalog = Datacatalog(uk="catalog-2", name="believe-duplicate").save()
    first_path = tmp_path / "first" / "sample.txt"
    second_path = tmp_path / "second" / "sample.txt"
    first_path.parent.mkdir()
    second_path.parent.mkdir()
    first_path.write_text("same bytes")
    second_path.write_text("same bytes")

    first = _record_file(first_path, catalog, compute_metadata=False)
    second = _record_file(second_path, catalog, compute_metadata=False)

    assert first.pk is not None
    assert second.pk == first.pk


def test_tree_clone_and_replace_path_create_a_new_draft_release(tmp_path, monkeypatch):
    old_phenotype = tmp_path / "old-phenotype.csv"
    genotype = tmp_path / "genotype.pgen"
    old_phenotype.write_text("old phenotype")
    genotype.write_text("genotype")
    catalog = Datacatalog(uk="catalog-clone", name="believe-clone").save()
    old_dataset = Dataset(uk="old-phenotype", path=str(old_phenotype), size=13).save()
    genotype_dataset = Dataset(uk="genotype", path=str(genotype), size=8).save()
    source_snapshot = TreeSnapshot(
        collection=catalog,
        name="believe-v1",
        source_root=str(tmp_path),
        state="published",
        manifest_content="snapshot: believe-v1\n",
        manifest_sha256="source-manifest",
    ).save()
    TreeEntry(
        snapshot=source_snapshot,
        relative_path="phenotypes",
        parent_path="",
        name="phenotypes",
        kind="directory",
        metadata={"role": "modality", "modality": "phenotype"},
    ).save()
    TreeEntry(
        snapshot=source_snapshot,
        relative_path="phenotypes/data.csv",
        parent_path="phenotypes",
        name="data.csv",
        kind="file",
        dataset=old_dataset,
    ).save()
    TreeEntry(
        snapshot=source_snapshot,
        relative_path="genotypes",
        parent_path="",
        name="genotypes",
        kind="directory",
    ).save()
    TreeEntry(
        snapshot=source_snapshot,
        relative_path="genotypes/data.pgen",
        parent_path="genotypes",
        name="data.pgen",
        kind="file",
        dataset=genotype_dataset,
    ).save()
    tree_module = importlib.import_module("omnia.cli.tree")
    monkeypatch.setattr(tree_module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(tree_module, "get_mongo_uri", lambda: "mongodb://unused")
    monkeypatch.setattr(tree_module, "get_datacatalog", lambda name: catalog)

    clone_result = CliRunner().invoke(tree, ["clone", "believe-clone", "believe-v1", "believe-v2"])

    target_snapshot = TreeSnapshot.objects(collection=catalog, name="believe-v2").first()
    assert clone_result.exit_code == 0, clone_result.output
    assert target_snapshot.state == "draft"
    assert target_snapshot.metadata["cloned_from"]["snapshot"] == "believe-v1"
    assert "snapshot: believe-v2" in target_snapshot.manifest_content
    cloned_phenotype = TreeEntry.objects(snapshot=target_snapshot, relative_path="phenotypes/data.csv").first()
    assert cloned_phenotype.dataset == old_dataset

    replacement = tmp_path / "new-phenotypes"
    replacement.mkdir()
    (replacement / "data.csv").write_text("new phenotype")
    replace_result = CliRunner().invoke(
        tree,
        ["replace-path", "believe-clone", "believe-v2", str(replacement), "phenotypes", "--skip-metadata-computation"],
    )

    target_snapshot.reload()
    phenotype_root = TreeEntry.objects(snapshot=target_snapshot, relative_path="phenotypes").first()
    replacement_file = TreeEntry.objects(snapshot=target_snapshot, relative_path="phenotypes/data.csv").first()
    assert replace_result.exit_code == 0, replace_result.output
    assert phenotype_root.metadata == {"role": "modality", "modality": "phenotype"}
    assert replacement_file.dataset != old_dataset
    cloned_genotype = TreeEntry.objects(snapshot=target_snapshot, relative_path="genotypes/data.pgen").first()
    assert cloned_genotype.dataset == genotype_dataset
    assert target_snapshot.manifest_sha256 is None
    assert target_snapshot.metadata["manifest_invalidated_by_replace"] is True
    assert target_snapshot.metadata["replacements"][0]["destination"] == "phenotypes"


def test_export_links_materializes_files_and_logical_aliases_atomically(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    source_file = source_root / "sample.txt"
    source_file.write_text("contents")
    catalog = Datacatalog(uk="catalog-3", name="believe-export").save()
    dataset = Dataset(uk="dataset-3", path=str(source_file), size=8).save()
    snapshot = TreeSnapshot(
        collection=catalog,
        name="published",
        source_root=str(source_root),
        state="published",
        manifest_sha256="abc",
    ).save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="data",
        parent_path="",
        name="data",
        kind="directory",
        metadata={"role": "modality", "modality": "genotype"},
    ).save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="data/sample.txt",
        parent_path="data",
        name="sample.txt",
        kind="file",
        dataset=dataset,
    ).save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="latest.txt",
        parent_path="",
        name="latest.txt",
        kind="alias",
        target_path="data/sample.txt",
    ).save()

    destination = tmp_path / "export"
    export_links(snapshot, destination, [source_root])

    assert (destination / "data/sample.txt").is_symlink()
    assert os.path.realpath(destination / "latest.txt") == str(source_file)
    assert '"snapshot": "published"' in (destination / ".omnia-snapshot.json").read_text()
    assert (destination.stat().st_mode & stat.S_IWUSR) == stat.S_IWUSR


def test_export_links_filters_to_a_curated_modality(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    genotype_file = source_root / "genotype.txt"
    proteome_file = source_root / "proteome.txt"
    genotype_file.write_text("genotype")
    proteome_file.write_text("proteome")
    catalog = Datacatalog(uk="catalog-5", name="believe-filter").save()
    genotype = Dataset(uk="dataset-5a", path=str(genotype_file), size=8).save()
    proteome = Dataset(uk="dataset-5b", path=str(proteome_file), size=8).save()
    snapshot = TreeSnapshot(collection=catalog, name="filtered", source_root=str(source_root), state="published").save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="genotypes",
        parent_path="",
        name="genotypes",
        kind="directory",
        metadata={"role": "modality", "modality": "genotype"},
    ).save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="genotypes/data.txt",
        parent_path="genotypes",
        name="data.txt",
        kind="file",
        dataset=genotype,
    ).save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="proteome",
        parent_path="",
        name="proteome",
        kind="directory",
        metadata={"role": "modality", "modality": "proteomics"},
    ).save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="proteome/data.txt",
        parent_path="proteome",
        name="data.txt",
        kind="file",
        dataset=proteome,
    ).save()

    destination = tmp_path / "genotype-export"
    export_links(snapshot, destination, [source_root], modality="genotype")

    assert (destination / "genotypes/data.txt").is_symlink()
    assert not (destination / "proteome").exists()


def test_export_links_rejects_retired_snapshot(tmp_path):
    catalog = Datacatalog(uk="catalog-retired", name="believe-retired").save()
    snapshot = TreeSnapshot(collection=catalog, name="old-freeze", source_root=str(tmp_path), state="retired").save()

    with pytest.raises(ValueError, match="Retired snapshots cannot be exported"):
        export_links(snapshot, tmp_path / "export", [tmp_path])


def test_tree_retire_preserves_snapshot_and_records_reason(monkeypatch):
    catalog = Datacatalog(uk="catalog-retire-command", name="believe-retire-command").save()
    snapshot = TreeSnapshot(
        collection=catalog, name="freeze-one", source_root="/project/believe", state="published"
    ).save()
    tree_module = importlib.import_module("omnia.cli.tree")
    monkeypatch.setattr(tree_module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(tree_module, "get_mongo_uri", lambda: "mongodb://unused")
    monkeypatch.setattr(tree_module, "get_datacatalog", lambda name: catalog)

    result = CliRunner().invoke(tree, ["retire", "believe-retire-command", "freeze-one", "--reason", "Superseded"])

    persisted = TreeSnapshot.objects(id=snapshot.id).first()
    assert result.exit_code == 0
    assert "retired" in result.output
    assert persisted.state == "retired"
    assert persisted.retired_at is not None
    assert persisted.retirement_reason == "Superseded"


def test_tree_add_path_adds_an_additional_directory_to_a_draft_snapshot(tmp_path, monkeypatch):
    source = tmp_path / "annex"
    source.mkdir()
    (source / "notes.txt").write_text("metadata")
    catalog = Datacatalog(uk="catalog-add-path", name="believe-add-path").save()
    snapshot = TreeSnapshot(collection=catalog, name="draft-with-annex", source_root="/project/believe").save()
    tree_module = importlib.import_module("omnia.cli.tree")
    monkeypatch.setattr(tree_module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(tree_module, "get_mongo_uri", lambda: "mongodb://unused")
    monkeypatch.setattr(tree_module, "get_datacatalog", lambda name: catalog)

    result = CliRunner().invoke(
        tree,
        ["add-path", "believe-add-path", "draft-with-annex", str(source), "extra/annex", "--skip-metadata-computation"],
    )

    persisted = TreeSnapshot.objects(id=snapshot.id).first()
    assert result.exit_code == 0, result.output
    assert TreeEntry.objects(snapshot=snapshot, relative_path="extra", kind="directory").first()
    assert TreeEntry.objects(snapshot=snapshot, relative_path="extra/annex", kind="directory").first()
    assert TreeEntry.objects(snapshot=snapshot, relative_path="extra/annex/notes.txt", kind="file").first()
    assert persisted.metadata["additional_sources"] == [{"source": str(source.resolve()), "destination": "extra/annex"}]


def test_tree_add_path_refuses_to_change_a_published_snapshot(tmp_path, monkeypatch):
    source = tmp_path / "additional.txt"
    source.write_text("data")
    catalog = Datacatalog(uk="catalog-add-published", name="believe-add-published").save()
    TreeSnapshot(collection=catalog, name="published", source_root="/project/believe", state="published").save()
    tree_module = importlib.import_module("omnia.cli.tree")
    monkeypatch.setattr(tree_module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(tree_module, "get_mongo_uri", lambda: "mongodb://unused")
    monkeypatch.setattr(tree_module, "get_datacatalog", lambda name: catalog)

    result = CliRunner().invoke(tree, ["add-path", "believe-add-published", "published", str(source), "extra.txt"])

    assert result.exit_code != 0
    assert "only be added to draft snapshots" in result.output


def test_tree_list_displays_snapshot_state_and_manifest(monkeypatch):
    catalog = Datacatalog(uk="catalog-4", name="believe-list").save()
    TreeSnapshot(
        collection=catalog,
        name="published-snapshot",
        source_root="/project/believe",
        state="published",
        manifest_sha256="manifest-checksum",
    ).save()
    tree_module = importlib.import_module("omnia.cli.tree")
    monkeypatch.setattr(tree_module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(tree_module, "get_mongo_uri", lambda: "mongodb://unused")
    monkeypatch.setattr(tree_module, "get_datacatalog", lambda name: catalog)

    result = CliRunner().invoke(tree, ["list", "believe-list"])

    assert result.exit_code == 0
    assert "published-snapshot\tpublished" in result.output
    assert "manifest-checksum" in result.output

import importlib
import json
from contextlib import nullcontext

import mongomock
from click.testing import CliRunner
from mongoengine import connect, disconnect

from omnia.cli.browse import browse
from omnia.cli.describe import describe_path
from omnia.cli.get import dataset_retrieval
from omnia.models.data_collection import Datacatalog
from omnia.models.data_object import Dataset
from omnia.models.data_tree import TreeEntry, TreeSnapshot


def setup_function():
    disconnect()
    connect("omnia_browse_test", host="mongodb://localhost", mongo_client_class=mongomock.MongoClient)


def teardown_function():
    disconnect()


def _fixture():
    catalog = Datacatalog(uk="catalog-browse", name="believe", description="BELIEVE study").save()
    dataset = Dataset(
        uk="dataset-browse", path="/private/data/chr1.pgen", size=42, included_in_datacatalog=[catalog]
    ).save()
    published = TreeSnapshot(
        collection=catalog, name="freeze-two", source_root="/private/data", state="published"
    ).save()
    retired = TreeSnapshot(collection=catalog, name="freeze-one", source_root="/private/data", state="retired").save()
    TreeEntry(
        snapshot=published,
        relative_path="genotypes",
        parent_path="",
        name="genotypes",
        kind="directory",
        metadata={"role": "modality", "modality": "genotype"},
    ).save()
    TreeEntry(
        snapshot=published,
        relative_path="genotypes/chr1.pgen",
        parent_path="genotypes",
        name="chr1.pgen",
        kind="file",
        dataset=dataset,
    ).save()
    return catalog, published, retired


def _browse_mongo(monkeypatch):
    module = importlib.import_module("omnia.cli.browse")
    monkeypatch.setattr(module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(module, "get_mongo_uri", lambda: "mongodb://unused")


def test_browse_lists_published_snapshots_and_hides_retired_by_default(monkeypatch):
    _fixture()
    _browse_mongo(monkeypatch)

    result = CliRunner().invoke(browse, ["snapshots", "believe", "--format", "json"])

    assert result.exit_code == 0, result.output
    assert [row["name"] for row in json.loads(result.output)] == ["freeze-two"]


def test_browse_lists_and_finds_logical_paths_without_backing_paths(monkeypatch):
    _fixture()
    _browse_mongo(monkeypatch)

    listing = CliRunner().invoke(browse, ["ls", "believe", "freeze-two", "genotypes", "--format", "json"])
    found = CliRunner().invoke(
        browse, ["find", "believe", "freeze-two", "--modality", "genotype", "--kind", "file", "--format", "json"]
    )

    assert listing.exit_code == 0, listing.output
    assert json.loads(listing.output) == [
        {"path": "genotypes/chr1.pgen", "name": "chr1.pgen", "kind": "file", "modality": None, "role": None, "size": 42}
    ]
    payload = json.loads(found.output)
    assert payload["total"] == 1
    assert payload["items"][0]["path"] == "genotypes/chr1.pgen"
    assert "/private/data" not in found.output


def test_browse_show_summarizes_modalities_and_known_size(monkeypatch):
    _fixture()
    _browse_mongo(monkeypatch)

    result = CliRunner().invoke(browse, ["show", "believe", "freeze-two", "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)[0]
    assert payload["files"] == 1
    assert payload["known_size_bytes"] == 42
    assert payload["modalities"] == ["genotype"]


def test_browse_describe_returns_file_metadata_without_backing_path(monkeypatch):
    _fixture()
    _browse_mongo(monkeypatch)

    result = CliRunner().invoke(
        browse, ["describe", "believe", "freeze-two", "genotypes/chr1.pgen", "--format", "json"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)[0]
    assert payload["path"] == "genotypes/chr1.pgen"
    assert payload["dataset_id"] == "dataset-browse"
    assert payload["size"] == 42
    assert payload["status"] == "available"
    assert "/private/data" not in result.output


def test_describe_uses_an_exported_view_marker_to_summarize_the_current_subtree(monkeypatch, tmp_path):
    _fixture()
    view_root = tmp_path / "believe-view"
    logical_directory = view_root / "genotypes"
    logical_directory.mkdir(parents=True)
    (view_root / ".omnia-snapshot.json").write_text(
        json.dumps({"catalog": "believe", "snapshot": "freeze-two"}), encoding="utf-8"
    )
    module = importlib.import_module("omnia.cli.describe")
    monkeypatch.setattr(module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(module, "get_mongo_uri", lambda: "mongodb://unused")

    result = CliRunner().invoke(describe_path, [str(logical_directory), "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)[0]
    assert payload["logical_path"] == "genotypes"
    assert payload["files"] == 1
    assert payload["known_size_bytes"] == 42
    assert "/private/data" not in result.output


def test_browse_find_with_no_matches_returns_an_empty_result(monkeypatch):
    _fixture()
    _browse_mongo(monkeypatch)

    result = CliRunner().invoke(browse, ["find", "believe", "freeze-two", "--name", "BELSLUM"])

    assert result.exit_code == 0, result.output
    assert "NAME" in result.output
    assert "0 matching entries" in result.output


def test_browse_ls_suggests_describe_for_a_file(monkeypatch):
    _fixture()
    _browse_mongo(monkeypatch)

    result = CliRunner().invoke(browse, ["ls", "believe", "freeze-two", "genotypes/chr1.pgen"])

    assert result.exit_code != 0
    assert "Use 'omnia browse describe believe freeze-two genotypes/chr1.pgen'" in result.output


def test_browse_ls_supports_recursive_sorting_and_human_readable_sizes(monkeypatch):
    _fixture()
    _browse_mongo(monkeypatch)

    result = CliRunner().invoke(
        browse, ["ls", "believe", "freeze-two", "--recursive", "--sort", "size", "--long", "--human-readable"]
    )

    assert result.exit_code == 0, result.output
    assert "genotypes" in result.output
    assert "chr1.pgen" in result.output
    assert "42 B" in result.output
    assert "TARGET_PATH" in result.output


def test_get_prints_paths_to_stdout_and_writes_only_when_requested(monkeypatch, tmp_path):
    catalog, _, _ = _fixture()
    get_module = importlib.import_module("omnia.cli.get")
    monkeypatch.setattr(get_module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(get_module, "get_mongo_uri", lambda: "mongodb://unused")
    monkeypatch.setattr(get_module, "get_datacatalog", lambda name: catalog)

    result = CliRunner().invoke(dataset_retrieval, ["believe"])
    output_path = tmp_path / "paths.txt"
    written = CliRunner().invoke(dataset_retrieval, ["believe", "--output", str(output_path)])

    assert result.exit_code == 0, result.output
    assert result.output == "/private/data/chr1.pgen\n"
    assert written.exit_code == 0, written.output
    assert output_path.read_text() == result.output

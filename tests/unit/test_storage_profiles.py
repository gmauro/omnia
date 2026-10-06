import importlib
from contextlib import nullcontext

import mongomock
from click.testing import CliRunner
from mongoengine import connect, disconnect

from omnia.cli.mount import _configured_or_explicit_roots, mount_datasets
from omnia.cli.tree import export_tree_links
from omnia.config.config_manager import ConfigurationManager
from omnia.config.config_models import Configuration
from omnia.filesystem import DatasetEntry
from omnia.models.data_collection import Datacatalog
from omnia.models.data_tree import TreeSnapshot


def setup_function():
    disconnect()
    connect("omnia_storage_profile_test", host="mongodb://localhost", mongo_client_class=mongomock.MongoClient)


def teardown_function():
    disconnect()


def _configuration() -> Configuration:
    return Configuration(
        default_profile="local",
        profiles={
            "local": {
                "prefix": "mongodb",
                "host": "localhost",
                "port": 27017,
                "database": "omnia",
                "options": {"connectTimeoutMS": 1, "socketTimeoutMS": 1, "retryWrites": "false"},
            }
        },
        default_storage_profile="believe-shared",
        storage_profiles={"believe-shared": {"storage_roots": ["/project/believe"], "allowed_catalogs": ["believe"]}},
    )


def test_storage_profile_resolution_uses_default_and_checks_catalogue_scope():
    manager = object.__new__(ConfigurationManager)
    manager.config = _configuration()

    assert manager.storage_roots("believe") == ["/project/believe"]
    assert manager.storage_roots("believe", "believe-shared") == ["/project/believe"]
    try:
        manager.storage_roots("other")
    except ValueError as error:
        assert "not configured for catalogue" in str(error)
    else:
        raise AssertionError("Expected a profile scope error")


def test_configuration_manager_retains_mongodb_uri_property_after_storage_profile_support():
    manager = object.__new__(ConfigurationManager)
    manager.profile = _configuration().profiles["local"]
    manager.uri_from_cli = None

    assert (
        manager.mongodb_uri == "mongodb://localhost:27017/omnia?connectTimeoutMS=1&socketTimeoutMS=1&retryWrites=false"
    )


def test_explicit_storage_roots_remain_an_advanced_override(tmp_path):
    root = tmp_path / "storage"
    root.mkdir()

    assert _configured_or_explicit_roots("believe", (root,), None) == [str(root)]


def test_mount_accepts_simple_snapshot_syntax_and_uses_configured_roots(monkeypatch, tmp_path):
    mount_module = importlib.import_module("omnia.cli.mount")
    calls = {}
    monkeypatch.setattr(
        mount_module,
        "get_storage_roots",
        lambda catalog, profile: calls.setdefault("roots", (catalog, profile)) and ["/project/believe"],
    )
    monkeypatch.setattr(
        mount_module,
        "_snapshot_entries",
        lambda catalog, snapshot, roots: (
            [DatasetEntry("dataset", "sample.txt", 1, relative_path="sample.txt")],
            [],
            [],
            object(),
            b"{}\n",
        ),
    )
    monkeypatch.setattr(
        mount_module,
        "fuse_mount",
        lambda tree, resolver, mountpoint, foreground: calls.update(
            {"mountpoint": mountpoint, "foreground": foreground, "marker": tree.node("/.omnia-snapshot.json").content}
        ),
    )

    result = CliRunner().invoke(
        mount_datasets, ["believe", "believe_20261001", str(tmp_path), "--storage-profile", "believe-shared"]
    )

    assert result.exit_code == 0, result.output
    assert calls["roots"] == ("believe", "believe-shared")
    assert calls["mountpoint"] == str(tmp_path)
    assert calls["marker"] == b"{}\n"


def test_export_links_uses_configured_roots_without_an_explicit_path(monkeypatch, tmp_path):
    catalog = Datacatalog(uk="catalog-storage", name="believe").save()
    snapshot = TreeSnapshot(
        collection=catalog, name="believe_20261001", source_root="/project/believe", state="published"
    ).save()
    tree_module = importlib.import_module("omnia.cli.tree")
    calls = {}
    monkeypatch.setattr(tree_module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(tree_module, "get_mongo_uri", lambda: "mongodb://unused")
    monkeypatch.setattr(tree_module, "get_datacatalog", lambda name: catalog)
    monkeypatch.setattr(
        tree_module,
        "get_storage_roots",
        lambda collection, profile: calls.setdefault("roots", (collection, profile)) and ["/project/believe"],
    )
    monkeypatch.setattr(
        tree_module,
        "export_links",
        lambda selected, destination, roots, modality: calls.update(
            {"snapshot": selected, "destination": destination, "resolved_roots": roots, "modality": modality}
        ),
    )

    destination = tmp_path / "view"
    result = CliRunner().invoke(
        export_tree_links,
        ["believe", "believe_20261001", str(destination), "--storage-profile", "believe-shared"],
    )

    assert result.exit_code == 0, result.output
    assert calls["roots"] == ("believe", "believe-shared")
    assert calls["resolved_roots"] == ["/project/believe"]
    assert calls["snapshot"] == snapshot

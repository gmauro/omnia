import importlib
from contextlib import nullcontext
from types import SimpleNamespace

import mongomock
from click.testing import CliRunner
from mongoengine import connect, disconnect

from omnia.cli.rm import dataset_delete
from omnia.models.data_collection import Datacatalog
from omnia.models.data_object import Dataset
from omnia.models.data_tree import TreeEntry, TreeSnapshot


def setup_function():
    disconnect()
    connect("omnia_rm_test", host="mongodb://localhost", mongo_client_class=mongomock.MongoClient)


def teardown_function():
    disconnect()


def test_rm_refuses_to_delete_a_dataset_referenced_by_a_snapshot(monkeypatch):
    path = "/project/believe/chr1.pgen"
    catalog = Datacatalog(uk="catalog-rm", name="believe-rm").save()
    dataset = Dataset(uk="dataset-rm", path=path).save()
    snapshot = TreeSnapshot(collection=catalog, name="freeze-one", source_root="/project/believe").save()
    TreeEntry(
        snapshot=snapshot,
        relative_path="genotypes/chr1.pgen",
        parent_path="genotypes",
        name="chr1.pgen",
        kind="file",
        dataset=dataset,
    ).save()
    rm_module = importlib.import_module("omnia.cli.rm")
    monkeypatch.setattr(rm_module, "get_mec", lambda uri: nullcontext())
    monkeypatch.setattr(rm_module, "get_mongo_uri", lambda: "mongodb://unused")
    monkeypatch.setattr(rm_module, "match_files", lambda source: [path])
    monkeypatch.setattr(rm_module, "get_data_object", lambda file_path: SimpleNamespace(mdb_obj=dataset))

    result = CliRunner().invoke(dataset_delete, [path])

    assert result.exit_code != 0
    assert "Refusing to delete" in result.output
    assert "genotypes/chr1.pgen" in result.output
    assert Dataset.objects(id=dataset.id).first() is not None

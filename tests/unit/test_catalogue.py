import importlib

from click.testing import CliRunner

from omnia.cli.catalogue import catalogue


def test_catalogue_group_exposes_the_preferred_lifecycle_commands():
    result = CliRunner().invoke(catalogue, ["--help"])

    assert result.exit_code == 0, result.output
    for command in ("create", "list", "describe", "verify", "update", "delete"):
        assert command in result.output


def test_catalogue_create_delegates_to_the_existing_create_implementation(monkeypatch):
    received = {}

    def create(name, description, keywords):
        received.update(name=name, description=description, keywords=keywords)

    module = importlib.import_module("omnia.cli.catalogue")
    monkeypatch.setattr(module.add_collection, "callback", create)

    result = CliRunner().invoke(
        catalogue,
        ["create", "example-project", "--description", "Example data", "--keywords", "omics", "--keywords", "qc"],
    )

    assert result.exit_code == 0, result.output
    assert received == {"name": "example-project", "description": "Example data", "keywords": ["omics", "qc"]}


def test_catalogue_verify_delegates_to_metadata_checksum_verification(monkeypatch):
    received = {}

    def list_metadata(source, full_path, verify_checksums):
        received.update(source=source, full_path=full_path, verify_checksums=verify_checksums)

    module = importlib.import_module("omnia.cli.catalogue")
    monkeypatch.setattr(module.list_metadata, "callback", list_metadata)

    result = CliRunner().invoke(catalogue, ["verify", "example-project"])

    assert result.exit_code == 0, result.output
    assert received == {"source": "example-project", "full_path": False, "verify_checksums": True}

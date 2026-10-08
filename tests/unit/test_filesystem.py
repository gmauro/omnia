import os
from datetime import datetime

import pytest

from omnia.filesystem import AliasEntry, DatasetEntry, OmniaVirtualTree, PosixObjectResolver, StorageRootError


def test_virtual_tree_exposes_unique_and_collision_safe_names():
    tree = OmniaVirtualTree(
        [
            DatasetEntry("alpha", "sample.bam", 10, datetime(2025, 1, 1)),
            DatasetEntry("beta", "sample.bam", 20),
            DatasetEntry("gamma", "notes.txt", 3),
        ]
    )

    assert tree.children("/") == ["notes.txt", "sample.bam--alpha", "sample.bam--beta"]
    assert tree.node("/sample.bam--alpha").entry.object_id == "alpha"
    assert tree.stat("/notes.txt")["st_size"] == 3
    assert tree.stat("/")["st_mode"] & 0o777 == 0o555
    with pytest.raises(FileNotFoundError):
        tree.node("/../private")


def test_virtual_tree_preserves_a_snapshot_hierarchy_and_empty_directories():
    tree = OmniaVirtualTree(
        [
            DatasetEntry(
                "pgen-1",
                "chr1.pgen",
                100,
                relative_path="genotypes/freeze-two/HDS_by_chr/chr1.pgen",
            )
        ],
        directories=["globus", "genotypes/freeze-two/HDS_by_chr"],
    )

    assert tree.children("/") == ["genotypes", "globus"]
    assert tree.children("/genotypes/freeze-two/HDS_by_chr") == ["chr1.pgen"]
    assert tree.node("/globus").is_directory
    assert tree.node("/genotypes/freeze-two/HDS_by_chr/chr1.pgen").entry.object_id == "pgen-1"


def test_virtual_tree_exposes_logical_aliases_without_physical_paths():
    tree = OmniaVirtualTree(
        [DatasetEntry("pgen-1", "chr1.pgen", 100, relative_path="data/chr1.pgen")],
        aliases=[AliasEntry("links/latest.pgen", "data/chr1.pgen")],
    )

    assert tree.children("/links") == ["latest.pgen"]
    assert tree.alias_target("/links/latest.pgen") == "../data/chr1.pgen"


def test_virtual_tree_exposes_read_only_snapshot_marker():
    tree = OmniaVirtualTree([], metadata_files={".omnia-snapshot.json": b'{"snapshot": "freeze-two"}\n'})

    assert tree.children("/") == [".omnia-snapshot.json"]
    assert tree.node("/.omnia-snapshot.json").content == b'{"snapshot": "freeze-two"}\n'
    assert tree.stat("/.omnia-snapshot.json")["st_size"] == len(b'{"snapshot": "freeze-two"}\n')


def test_resolver_reads_only_registered_regular_files(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    data_file = root / "sample.txt"
    data_file.write_text("hello")
    resolver = PosixObjectResolver([root])
    resolver.register("object-1", data_file)

    fd = resolver.open("object-1")
    try:
        assert os.read(fd, 5) == b"hello"
    finally:
        os.close(fd)

    with pytest.raises(FileNotFoundError):
        resolver.open("not-registered")


def test_resolver_rejects_paths_outside_root_and_symlinks(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("private")
    resolver = PosixObjectResolver([root])

    with pytest.raises(StorageRootError, match="outside"):
        resolver.register("outside", outside)

    link = root / "link.txt"
    link.symlink_to(outside)
    with pytest.raises(StorageRootError, match="symlink"):
        resolver.register("link", link)

"""Versioned logical directory trees for catalogue datasets."""

import datetime

from mongoengine import DateTimeField, Document, ReferenceField, StringField

from omnia.models.commons import JSONField
from omnia.models.data_collection import Datacatalog
from omnia.models.data_object import Dataset


class TreeSnapshot(Document):
    """An immutable, publishable logical view of one data catalogue."""

    collection = ReferenceField(Datacatalog, required=True)
    name = StringField(max_length=200, required=True)
    source_root = StringField(required=True)
    state = StringField(choices=("draft", "published", "retired"), default="draft", required=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    published_at = DateTimeField()
    retired_at = DateTimeField()
    retirement_reason = StringField(max_length=2000)
    metadata = JSONField()
    manifest_content = StringField()
    manifest_sha256 = StringField(max_length=64)

    meta = {
        "collection": "tree_snapshots",
        "indexes": [{"fields": ("collection", "name"), "unique": True}],
    }


class TreeEntry(Document):
    """One directory, file, or logical alias in a :class:`TreeSnapshot`."""

    snapshot = ReferenceField(TreeSnapshot, required=True)
    relative_path = StringField(max_length=2000, required=True)
    parent_path = StringField(max_length=2000, required=True)
    name = StringField(max_length=500, required=True)
    kind = StringField(choices=("directory", "file", "alias"), required=True)
    dataset = ReferenceField(Dataset)
    target_path = StringField(max_length=2000)
    metadata = JSONField()

    meta = {
        "collection": "tree_entries",
        "indexes": [
            {"fields": ("snapshot", "relative_path"), "unique": True},
            "snapshot",
            "parent_path",
        ],
    }

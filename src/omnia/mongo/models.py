"""
Data virtualization module
"""

import datetime
import json
import platform

from mongoengine import DateTimeField, Document, IntField, ListField, ReferenceField, StringField, ValidationError

from omnia import logger
from omnia.mongo.mixin import MongoMixin
from omnia.utils import Hashing, get_file_size, guess_mimetype

PREFIXES = ("posix", "s3", "https")


class JSONField(StringField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_mongo(self, value):
        if value is not None:
            try:
                return json.dumps(value)
            except TypeError as e:
                raise ValidationError(f"Invalid JSON value: {e}") from e
        return value

    def to_python(self, value):
        if value is not None and isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON string: {e}") from e
        return value

    def validate(self, value):
        if value is not None and not isinstance(value, str | dict | list):
            raise ValidationError("Invalid JSON value")


class Dataset(Document):
    """Base class for a set of data objects."""

    title = StringField(max_length=200, sparse=True, required=True, unique=True)
    description = StringField(max_length=200)
    tags = ListField(StringField(max_length=50))

    @classmethod
    def json_dict_fields(cls) -> tuple:
        """
        Returns a tuple of field names in this metadata class that store JSON-formatted data.

        These fields are stored as strings in MongoDB, where each string contains a valid JSON object.
        The purpose of this method is to provide a convenient way to access these JSON-formatted fields.

        :return: A tuple of field names (str) that store JSON-formatted data
        """
        return tuple(field.name for field in cls._fields.values() if isinstance(field, JSONField))


class DataCollection(MongoMixin):
    """Represents a collection of data objects"""

    def __init__(self, **kwargs):
        self.logger = logger
        self._klass = kwargs.get("klass", Dataset)

        self._obj = self._klass(
            title=kwargs.get("title"),
            description=kwargs.get("description", None),
            tags=kwargs.get("tags", []),
        )

    @property
    def klass(self) -> type:
        """Get the class of the underlying MongoDB object."""
        return self._klass

    @property
    def mdb_obj(self) -> Dataset:
        """Get the underlying MongoDB object."""
        return self._obj

    @property
    def pk(self) -> str:
        """
        the primary key of the object known by MongoDB (a.k.a _id)
        """
        return self._obj.pk

    @property
    def unique_key(self) -> str:
        """Get a unique key for the object."""
        return f"{self.mdb_obj.title}"

    @property
    def unique_key_dict(self) -> dict:
        """Get a unique key  for the object."""
        return {"title": self.mdb_obj.title}


class DataObject(Document):
    """Base class for data objects."""

    checksum = StringField()
    collections = ListField(ReferenceField(Dataset))
    creation_date = DateTimeField(default=datetime.datetime.now())
    data_id = StringField(max_length=25, required=True, unique=True)
    description = StringField(max_length=200)
    file_size = IntField()
    host = StringField(required=True)
    mimetype = StringField()
    modification_date = DateTimeField()
    path = StringField(required=True)
    prefix = StringField(choices=PREFIXES)
    tags = ListField(StringField(max_length=50))

    @classmethod
    def json_dict_fields(cls) -> tuple:
        """
        Returns a tuple of field names in this metadata class that store JSON-formatted data.

        These fields are stored as strings in MongoDB, where each string contains a valid JSON object.
        The purpose of this method is to provide a convenient way to access these JSON-formatted fields.

        :return: A tuple of field names (str) that store JSON-formatted data
        """
        return tuple(field.name for field in cls._fields.values() if isinstance(field, JSONField))

    meta = {"allow_inheritance": True}


class PosixDataObject(MongoMixin):
    """Represents a POSIX data object."""

    def __init__(self, **kwargs):
        """Initialize a PosixDataObject instance.

        Args:
            **kwargs: Keyword arguments for initializing the object.
        """
        self.logger = logger
        self._klass = kwargs.get("klass", DataObject)

        self._obj = self._klass(
            collections=kwargs.get("collections", []),
            data_id=kwargs.get("data_id"),
            host=kwargs.get("host", platform.node()),
            path=kwargs.get("path"),
            prefix="posix",
            checksum=None,
            file_size=None,
            mimetype=None,
        )

    # required attributes
    @property
    def klass(self) -> type:
        """Get the class of the underlying MongoDB object."""
        return self._klass

    @property
    def mdb_obj(self) -> DataObject:
        """Get the underlying MongoDB object."""
        return self._obj

    @property
    def pk(self) -> str:
        """
        the primary key of the object known by MongoDB (a.k.a _id)
        """
        return self._obj.pk

    @property
    def unique_key(self) -> str:
        """Get a unique key for the object."""
        return f"{self.mdb_obj.data_id}"

    @property
    def unique_key_dict(self) -> dict:
        """Get a unique key  for the object."""
        return {"data_id": self.mdb_obj.data_id}

    # end of required attributes

    def compute(self):
        """
        Retrieve object's detail
        """
        hg = Hashing()
        self.mdb_obj.checksum = hg.compute_file_hash(path=self.mdb_obj.path)
        self.mdb_obj.file_size = get_file_size(self.mdb_obj.path)
        self.mdb_obj.mimetype = guess_mimetype(self.mdb_obj.path)

        self.logger.debug(
            f"for {self.unique_key} computed:\n"
            f"{self.mdb_obj.file_size}, {self.mdb_obj.mimetype}, {self.mdb_obj.checksum}"
        )
        return self

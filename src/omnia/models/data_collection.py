import datetime

from mongoengine import DateTimeField, Document, ListField, StringField

from omnia import logger
from omnia.models.commons import JSONField
from omnia.mongo.mixin import MongoMixin
from omnia.utils import Hashing


class Dataset(Document):
    """Base class for a set of data objects."""

    uk = StringField(max_length=200, sparse=True, required=True, unique=True)
    title = StringField(max_length=200, sparse=True, required=True, unique_with=["uk"])
    description = StringField(max_length=200)
    creation_date = DateTimeField(default=datetime.datetime.now())
    modification_date = DateTimeField()
    tags = ListField(StringField(max_length=50))
    notes = JSONField()

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
            pk=kwargs.get("pk"),
            title=kwargs.get("title"),
            description=kwargs.get("description", None),
            tags=kwargs.get("tags", []),
        )

        self.make_unique_key()

    @property
    def desc(self) -> str:
        """Get object descriptor"""
        return f"{self.mdb_obj.title}"

    @property
    def klass(self) -> type:
        """Get the class of the underlying MongoDB object."""
        return self._klass

    @property
    def mdb_obj(self) -> Dataset:
        """Get the underlying MongoDB object."""
        return self._obj

    @property
    def pk(self) -> dict:
        """
        the primary key of the object known by MongoDB (a.k.a _id)
        """
        return {"pk": self.mdb_obj.pk}

    @property
    def unique_key(self) -> dict:
        """Get a unique key for the object."""
        return {"uk": self.mdb_obj.uk}

    def make_unique_key(self) -> None:
        """Generate a unique key for the object"""
        if self.mdb_obj.title:
            hg = Hashing()
            self.mdb_obj.uk = hg.compute_string_hash(self.mdb_obj.title)

    def set_modification_date(self) -> None:
        """Set the modification_date of the underlying MongoDB object"""
        self.mdb_obj.modification_date = datetime.datetime.now()

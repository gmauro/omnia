import datetime
import platform

from mongoengine import DateTimeField, Document, IntField, ListField, ReferenceField, StringField

from omnia import logger
from omnia.models.commons import PREFIXES, JSONField
from omnia.models.data_collection import Dataset
from omnia.mongo.mixin import MongoMixin
from omnia.utils import Hashing, get_file_size, guess_mimetype


class DataObject(Document):
    """Base class for data objects."""

    uk = StringField(max_length=25, sparse=True, required=True, unique=True)
    checksum = StringField()
    collections = ListField(ReferenceField(Dataset))
    creation_date = DateTimeField(default=datetime.datetime.now())
    # data_id = StringField(max_length=25, required=True, unique=True)
    file_size = IntField()
    host = StringField()
    mimetype = StringField()
    modification_date = DateTimeField()
    path = StringField(required=True)
    prefix = StringField(choices=PREFIXES)

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
        self.hg = Hashing()
        self.logger = logger
        self._klass = DataObject

        collections = kwargs.get("collections", [])
        host = kwargs.get("host", platform.node())
        path = kwargs.get("path")
        prefix = "posix"

        self._obj = self._klass(
            pk=kwargs.get("pk"),
            collections=collections,
            host=host,
            path=path,
            prefix=prefix,
            checksum=None,
            file_size=None,
            mimetype=None,
        )

        self.make_unique_key()

    # required attributes
    @property
    def desc(self):
        return f"{self.mdb_obj.uk}-{self.mdb_obj.path}"

    @property
    def klass(self) -> type:
        """Get the class of the underlying MongoDB object."""
        return self._klass

    @property
    def mdb_obj(self) -> DataObject:
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

    # end of required attributes

    def compute(self):
        """
        Retrieve object's detail
        """
        self.mdb_obj.checksum = self.hg.compute_file_hash(path=self.mdb_obj.path)
        self.mdb_obj.file_size = get_file_size(self.mdb_obj.path)
        self.mdb_obj.mimetype = guess_mimetype(self.mdb_obj.path)

        self.logger.debug(
            f"for {self.desc} computed:\n{self.mdb_obj.file_size}, {self.mdb_obj.mimetype}, {self.mdb_obj.checksum}"
        )
        return self

    def make_unique_key(self):
        """Generate a unique key for the object"""
        self.mdb_obj.uk = self.hg.compute_hash(fpath=self.mdb_obj.path)

    def set_modification_date(self) -> None:
        """Set the modification_date of the underlying MongoDB object"""
        self.mdb_obj.modification_date = datetime.datetime.now()

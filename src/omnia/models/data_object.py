import datetime
import platform

from mongoengine import DateTimeField, Document, IntField, ListField, ReferenceField, StringField

from omnia import logger
from omnia.models.commons import PROTOCOLS, JSONField
from omnia.models.data_collection import Datacatalog
from omnia.mongo.mixin import MongoMixin
from omnia.utils import Hashing, get_file_size, guess_mimetype


class Dataset(Document):
    """MongoEngine model for a BioSchemas Dataset

    Attributes:
        uk (StringField): Unique identifier for the dataset.
        checksum (StringField): Checksum value for the dataset.
        included_in_datacatalog (ListField): List of references to Datacatalog documents.
        date_created (DateTimeField): Date and time when the dataset was created.
        size (IntField): Size of the dataset in bytes.
        host (StringField): Host where the dataset is stored.
        encoding_format (StringField): Format of the dataset encoding.
        date_modified (DateTimeField): Date and time when the dataset was last modified.
        path (StringField): Path to the dataset.
        protocol (StringField): Prefix for the dataset, must be one of the predefined choices.
    """

    # JSON-LD context and type
    context = StringField(default="https://schema.org/", required=True)
    type = StringField(default="Dataset", required=True)

    # Dataset fields
    uk = StringField(max_length=25, required=True, unique=True)
    checksum = StringField()
    date_created = DateTimeField(default=datetime.datetime.now())
    date_modified = DateTimeField()
    encoding_format = StringField()
    host = StringField()
    included_in_datacatalog = ListField(ReferenceField(Datacatalog))
    path = StringField(required=True)
    protocol = StringField(choices=PROTOCOLS)
    size = IntField()

    @classmethod
    def json_dict_fields(cls) -> tuple:
        """
        Returns a tuple of field names in this metadata class that store JSON-formatted data.

        These fields are stored as strings in MongoDB, where each string contains a valid JSON object.
        The purpose of this method is to provide a convenient way to access these JSON-formatted fields.

        :return: A tuple of field names (str) that store JSON-formatted data
        """
        return tuple(field.name for field in cls._fields.values() if isinstance(field, JSONField))

    meta = {"collection": "datasets"}


class PosixDataObject(MongoMixin):
    """Represents a POSIX data object."""

    def __init__(self, **kwargs):
        """Initialize a PosixDataObject instance.

        Args:
            **kwargs: Keyword arguments for initializing the object.
        """
        self.hg = Hashing()
        self.logger = logger
        self._klass = Dataset

        included_in_datacatalog = kwargs.get("included_in_datacatalog", [])
        host = kwargs.get("host", platform.node())
        path = kwargs.get("path")
        protocol = "posix"

        self._obj = self._klass(
            pk=kwargs.get("pk"),
            included_in_datacatalog=included_in_datacatalog,
            host=host,
            path=path,
            protocol=protocol,
            checksum=None,
            size=None,
            encoding_format=None,
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

    # end of required attributes

    def compute(self):
        """
        Retrieve object's detail
        """
        self.mdb_obj.checksum = self.hg.compute_file_hash(path=self.mdb_obj.path)
        self.mdb_obj.size = get_file_size(self.mdb_obj.path)
        self.mdb_obj.encoding_format = guess_mimetype(self.mdb_obj.path)

        self.logger.debug(
            f"for {self.desc} computed:\n{self.mdb_obj.size}, {self.mdb_obj.encoding_format}, {self.mdb_obj.checksum}"
        )
        return self

    def make_unique_key(self):
        """Generate a unique key for the object"""
        self.mdb_obj.uk = self.hg.compute_hash(fpath=self.mdb_obj.path)

    def set_modification_date(self) -> None:
        """Set the modification_date of the underlying MongoDB object"""
        self.mdb_obj.date_modified = datetime.datetime.now()

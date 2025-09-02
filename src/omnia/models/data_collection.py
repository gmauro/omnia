import datetime

from mongoengine import (
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    ListField,
    StringField,
    URLField,
)

from omnia import logger
from omnia.models.commons import JSONField
from omnia.mongo.mixin import MongoMixin
from omnia.utils import Hashing


class Provider(EmbeddedDocument):
    """Embedded document for the provider of the datacatalog."""

    type = StringField(default="Organization", required=True)
    name = StringField(required=True)
    url = URLField()


class Datacatalog(Document):
    """MongoEngine model for a BioSchemas Datacatalog.

    Attributes:
        context (StringField): JSON-LD context
        type (StringField): Schema.org/Bioschemas class for the resource
        uk (StringField): Unique identifier for the catalog (max 200 chars)
        name (StringField): Unique name of the catalog (max 200 chars)
        description (StringField): Description of the catalog (max 200 chars)
        date_created (DateTimeField): Creation date, defaults to current datetime
        date_modified (DateTimeField): Last modification date
        keywords (ListField): List of keywords describing the catalog delimited by commas.
        notes (JSONField): Additional notes or metadata
        provider (EmbeddedDocumentField): Contact information about the catalog provider

    """

    # JSON-LD context and type
    context = StringField(default="https://schema.org/", required=True)
    type = StringField(default="Datacatalog", required=True)

    # Datacatalog fields
    uk = StringField(max_length=100, required=True, unique=True)
    name = StringField(max_length=200, required=True, unique=True)
    description = StringField(max_length=200)
    date_created = DateTimeField(default=datetime.datetime.now())
    date_modified = DateTimeField()
    keywords = ListField(StringField(max_length=100))
    notes = JSONField()

    # Nested documents
    provider = EmbeddedDocumentField(Provider)

    meta = {
        "collection": "data_catalogs",
        "indexes": [
            "name",
            "keywords",
        ],
    }

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
        self._klass = kwargs.get("klass", Datacatalog)

        self._obj = self._klass(
            pk=kwargs.get("pk"),
            name=kwargs.get("name"),
            description=kwargs.get("description", None),
            keywords=kwargs.get("keywords", []),
        )

        self.make_unique_key()

    @property
    def desc(self) -> str:
        """Get object descriptor"""
        return f"{self.mdb_obj.name}"

    @property
    def klass(self) -> type:
        """Get the class of the underlying MongoDB object."""
        return self._klass

    @property
    def mdb_obj(self) -> Datacatalog:
        """Get the underlying MongoDB object."""
        return self._obj

    @property
    def pk(self) -> dict:
        """
        the primary key of the object known by MongoDB (a.k.a. _id)
        """
        return {"pk": self.mdb_obj.pk}

    @property
    def unique_key(self) -> dict:
        """Get a unique key for the object."""
        return {"uk": self.mdb_obj.uk}

    def make_unique_key(self) -> None:
        """Generate a unique key for the object"""
        if self.mdb_obj.name:
            hg = Hashing()
            self.mdb_obj.uk = hg.compute_string_hash(self.mdb_obj.name)

    def set_modification_date(self) -> None:
        """Set the modification date of the underlying MongoDB object"""
        self.mdb_obj.date_modified = datetime.datetime.now()

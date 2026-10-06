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

from omnia.models.commons import JSONField
from omnia.models.mixin import MongoMixin, MongoWrapperMixin


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


class DataCollection(MongoMixin, MongoWrapperMixin):
    """Represents a data catalogue of registered datasets."""

    def __init__(self, **kwargs):
        # Pass the concrete Document class to the mix‑in base‑class
        super().__init__(klass=Datacatalog, **kwargs)

    # ------------------------------------------------------------------
    #  Concrete implementation required by MongoWrapperMixin
    # ------------------------------------------------------------------
    def _build_obj(self, **kwargs):
        """Create the underlying ``Datacatalog`` document."""
        return self._klass(
            pk=kwargs.get("pk"),
            name=kwargs.get("name"),
            description=kwargs.get("description", None),
            keywords=kwargs.get("keywords", []),
        )

    @property
    def desc(self) -> str:
        """Human‑readable descriptor."""
        return f"{self.mdb_obj.name}"

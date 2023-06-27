import datetime
from enum import Enum

from mongoengine import (
    DateTimeField,
    Document,
    EnumField,
    ListField,
    ReferenceField,
    StringField,
    URLField,
)

from omnia.connection import get_mec
from omnia.mixin import MongoMixin
from omnia.utils import is_a_valid_identifier


def validate_identifier(i, custom_list=None):
    list_to_check_against = custom_list if custom_list else [dtype.value for _, dtype in enumerate(DataType)]

    return is_a_valid_identifier(list_to_check_against, i)


def get_datatype(i):
    identifier = validate_identifier(i)
    return DataType(identifier.split("_")[0])


# Data identifier
# An identifier that uniquely distinguishes one set of data from all others.
# Examples include: Archival Resource Key (ARK); Digital Object Identifiers (DOI);
# Extensible Resource Identi?er (XRI); HANDLE; Life Science ID (LSID);
# Object Identifiers (OID); Persistent Uniform Resource Locators (PURL);
# URI/URN/URL; UUID.


class DataType(Enum):
    ARTICLE = "article"
    EQTL = "eqtl"
    GWAS = "gwas"
    PQTL = "pqtl"


class DataIdentifier(Document):
    unique_key = StringField(max_length=200, unique=True, required=True)
    datatype = EnumField(DataType, required=True)
    description = StringField(max_length=500)
    creation_date = DateTimeField(default=datetime.datetime.now())
    modification_date = DateTimeField()
    url = URLField()
    tags = ListField(StringField(max_length=50))

    meta = {"allow_inheritance": True}


class Reference(DataIdentifier):
    title = StringField(max_length=200, sparse=True, required=True, unique=True)
    ext_uid = StringField(max_length=200, sparse=True, unique=True)  # doi:..., pmid:...


class ReferenceID(MongoMixin):
    def __init__(self, **kwargs):
        uk = validate_identifier(kwargs.get("uk"), [DataType.ARTICLE.value])
        title = kwargs.get("title", None)
        datatype = DataType.ARTICLE
        description = kwargs.get("description", None)
        self._klass = kwargs.get("klass", Reference)
        url = kwargs.get("url", None)
        ext_uid = kwargs.get("uid", None)

        self._mec = kwargs.get("mec", get_mec())
        self._obj = self._klass(
            unique_key=uk, title=title, datatype=datatype, description=description, url=url, ext_uid=ext_uid
        )

    @property
    def pk(self):
        """
        the primary key of the object known by MongoDB
        """
        return self._obj.pk

    @property
    def mec(self):
        return self._mec

    @property
    def mdb_obj(self):
        return self._obj

    @property
    def klass(self):
        return self._klass

    @property
    def uk(self):
        """
        the unique key of the object known by the user
        """
        return self._obj.unique_key

    @uk.setter
    def uk(self, d):
        self._obj.unique_key = validate_identifier(d)

    @property
    def title(self):
        return self._obj.title

    @title.setter
    def title(self, t):
        self._obj.title = t

    @property
    def description(self):
        return self._obj.description

    @description.setter
    def description(self, d):
        self._obj.description = d

    @property
    def url(self):
        return self._obj.url

    @url.setter
    def url(self, u):
        self._obj.url = u

    @property
    def uid(self):
        return self._obj.ext_uid

    @uid.setter
    def uid(self, u):
        self._obj.ext_uid = u


class GvsTrait(DataIdentifier):
    notes = ListField(StringField(max_length=500))
    references = ListField(ReferenceField(Reference))


class GvsTraitID(MongoMixin):
    def __init__(self, **kwargs):
        uk = validate_identifier(kwargs.get("uk"))
        datatype = kwargs.get("datatype", get_datatype(uk))
        description = kwargs.get("description", None)
        notes = kwargs.get("notes", None)
        self._klass = kwargs.get("klass", GvsTrait)
        tags = kwargs.get("tags", [])
        url = kwargs.get("url", None)
        references = kwargs.get("references", [])

        self._mec = kwargs.get("mec", get_mec())
        self._obj = self._klass(
            unique_key=uk,
            datatype=datatype,
            description=description,
            notes=notes,
            url=url,
            tags=tags,
            references=references,
        )

    @property
    def pk(self):
        """
        the primary key of the object known by MongoDB
        """
        return self._obj.pk

    @property
    def mec(self):
        return self._mec

    @property
    def mdb_obj(self):
        return self._obj

    @property
    def klass(self):
        return self._klass

    @property
    def uk(self):
        """
        the unique key of the object known by the user
        """
        return self._obj.unique_key

    @uk.setter
    def uk(self, d):
        self._obj.unique_key = validate_identifier(d, [DataType.GWAS.value])

    @property
    def datatype(self):
        return self._obj.datatype

    @property
    def description(self):
        return self._obj.description

    @description.setter
    def description(self, d):
        self._obj.description = d

    @property
    def notes(self):
        return self._obj.notes

    @notes.setter
    def notes(self, notes):
        for note in notes:
            if note not in self._obj.notes:
                self._obj.notes.append(note)

    @property
    def tags(self):
        return self._obj.tags

    @tags.setter
    def tags(self, tags):
        for tag in tags:
            if tag not in self._obj.tags:
                self._obj.tags.append(tag)

    @property
    def url(self):
        return self._obj.url

    @url.setter
    def url(self, u):
        self._obj.url = u

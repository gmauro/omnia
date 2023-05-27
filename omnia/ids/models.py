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

# Data identifier
# An identifier that uniquely distinguishes one set of data from all others.
# Examples include: Archival Resource Key (ARK); Digital Object Identiers (DOI);
# Extensible Resource Identi?er (XRI); HANDLE; Life Science ID (LSID);
# Object Identi?ers (OID); Persistent Uniform Resource Locators (PURL);
# URI/URN/URL; UUID.


class DataType(Enum):
    GWAS = "gwas"


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
    title = StringField(max_length=200, unique=True)
    uid = StringField(max_length=200, unique=True)  # doi:..., pmid:...


class GwasDataIdentifier(DataIdentifier):
    note = StringField(max_length=500)
    references = ListField(ReferenceField(Reference))


class GwasDataID(MongoMixin):
    def __init__(self, **kwargs):
        uk = is_a_valid_identifier(DataType.GWAS.value, kwargs.get("uk"))
        datatype = DataType.GWAS
        description = kwargs.get("description", None)
        self._klass = kwargs.get("klass", GwasDataIdentifier)
        tags = kwargs.get("tags", [])
        url = kwargs.get("url", None)

        self._mec = kwargs.get("mec", get_mec())
        self._obj = self._klass(
            unique_key=uk,
            datatype=datatype,
            description=description,
            url=url,
            tags=tags,
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
        self._obj.unique_key = is_a_valid_identifier(DataType.GWAS.value, d)

    @property
    def description(self):
        return self._obj.description

    @description.setter
    def description(self, d):
        self._obj.description = d

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

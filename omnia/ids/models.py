from enum import Enum

from mongoengine import (
    Document,
    EnumField,
    ListField,
    ReferenceField,
    SequenceField,
    StringField,
    URLField,
)

from omnia.config_manager import ConfigurationManager

cm = ConfigurationManager()


class Reference(Document):
    title = StringField(max_length=200, unique=True)
    description = StringField(max_length=500)
    url = URLField()
    uid = StringField(max_length=200)  # Doi: ..., Pmid: ...


class Label(Enum):
    GWAS = "gwas"


class DataIdentifier(Document):
    label = EnumField(Label, required=True)
    description = StringField(max_length=500)
    counter = SequenceField()
    url = URLField()
    references = ListField(ReferenceField(Reference))


# class GwasDataID:
#     def __init__(self, **kwargs):
#         label = kwargs.get('label', Label.GWAS)
#         description = kwargs.get("description", None)
#         url = kwargs.get("url", None)
#
#         self.gdid = DataId(label=label, description=description, url=url)
#
#     @property
#     def id(self):
#         return self.gdid

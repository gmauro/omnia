from enum import Enum

from mongoengine import (
    Document,
    EnumField,
    SequenceField,
    StringField,
    URLField,
)

from omnia.config_manager import ConfigurationManager

cm = ConfigurationManager()


class Label(Enum):
    GWAS = "gwas"


class DataIdentifier(Document):
    label = EnumField(Label, required=True)
    description = StringField(max_length=200)
    counter = SequenceField()
    url = URLField()


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

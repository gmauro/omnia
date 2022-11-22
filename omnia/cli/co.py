from mongoengine.errors import NotUniqueError

from omnia.cli import get_mec
from omnia.dv.models import DataCollection

help_doc = """
Create a collection.
It reloads all attributes from the database, if the document has been saved
before.
"""


def make_parser(parser):
    parser.add_argument("label", type=str, help="Collection's label")


def implementation(logger, args):
    mec = get_mec(args)
    cobj = DataCollection(label=args.label)
    cobj._meta["db_alias"] = mec.alias
    try:
        with mec:
            cobj.save()
            logger.info("{} collection created".format(args.label))
    except NotUniqueError:
        logger.info(
            "Collection {} is present already. Creation skipped".format(
                args.label
            )
        )


def do_register(registration_list):
    registration_list.append(("co", help_doc, make_parser, implementation))

from mongoengine.errors import NotUniqueError

from omnia.connection import get_mec
from omnia.dv.models import DataCollection

help_doc = """
Create a collection.
Reloads all attributes from the database, if the document was saved before.
"""


def make_parser(parser):
    parser.add_argument("label", type=str, help="Collection's label")


def implementation(logger, args):
    mec = get_mec(db=args.db, uri=args.uri)
    cobj = DataCollection(label=args.label)
    # cobj._meta["db_alias"] = mec.alias
    try:
        with mec:
            cobj.save()
            print("here")
            logger.info("{} collection created".format(args.label))
    except NotUniqueError:
        logger.info("Collection {} already exists. Skipped creation ".format(args.label))


def do_register(registration_list):
    registration_list.append(("co", help_doc, make_parser, implementation))

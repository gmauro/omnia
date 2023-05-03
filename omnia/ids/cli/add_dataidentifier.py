from mongoengine.errors import NotUniqueError

from omnia.connection import get_mec
from omnia.ids.models import DataIdentifier, Reference

help_doc = """
Create a new Data identifier
"""


def make_parser(parser):
    parser.add_argument(
        "-l",
        "--label",
        type=str,
        metavar="LABEL",
        help="Label to use for the new data identifier",
    )
    parser.add_argument(
        "-d",
        "--description",
        type=str,
        help="Description of the new data identifier",
    )
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        help="URL of the new data identifier",
    )
    parser.add_argument(
        "-t",
        "--title",
        type=str,
        help="Title of the article",
    )


def implementation(logger, args):
    mec = get_mec(db=args.db, uri=args.uri)

    try:
        with mec:
            reference = Reference.objects(title=args.title)[0]
            did = DataIdentifier(label=args.label, description=args.description, url=args.url, references=[reference])
            did.save()
            logger.info("{} DataId created".format(args.label))
    except NotUniqueError:
        logger.info("DataId {} already exists. Skipped creation ".format(args.label))
    print("{}_{}".format(did.label, did.counter))


def do_register(registration_list):
    registration_list.append(("create", help_doc, make_parser, implementation))

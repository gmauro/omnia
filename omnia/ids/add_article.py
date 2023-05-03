from mongoengine.errors import NotUniqueError

from omnia.connection import get_mec
from omnia.ids.models import Reference

help_doc = """
Create a new Article object
"""


def make_parser(parser):
    parser.add_argument(
        "-t",
        "--title",
        type=str,
        help="Title of the article",
    )
    parser.add_argument(
        "-d",
        "--description",
        type=str,
        help="Description of the new data identifier",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="URL of the new data identifier",
    )
    parser.add_argument(
        "--uid",
        type=str,
        help="unique id of the article e.g.: doi:... pmid:...",
    )


def implementation(logger, args):
    mec = get_mec(db=args.db, uri=args.uri)

    try:
        with mec:
            article = Reference(title=args.title, description=args.description, url=args.url, uid=args.uid)
            article.save()
            logger.info("{} article created".format(args.title))
    except NotUniqueError:
        logger.info("DataId {} already exists. Skipped creation ".format(args.title))


def do_register(registration_list):
    registration_list.append(("add_article", help_doc, make_parser, implementation))

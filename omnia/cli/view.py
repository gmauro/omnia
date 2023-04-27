import pprint

from omnia.connection import get_mec
from omnia.dv.models import PosixDataObject

help_doc = """
View the details of the Omnia document if it has already been saved.
"""


def make_parser(parser):
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        metavar="PATH",
        help="Path of the registered file",
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Hostname of the registered file",
    )


def implementation(logger, args):
    mec = get_mec(db=args.db, uri=args.uri)
    dobj = PosixDataObject(logger=logger, mec=mec, path=args.path, host=args.host)
    pp = pprint.PrettyPrinter(indent=2, width=30, compact=True)
    pp.pprint(dobj.view())


def do_register(registration_list):
    registration_list.append(("view", help_doc, make_parser, implementation))

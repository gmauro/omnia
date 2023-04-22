import argparse

from omnia.connection import get_mec
from omnia.dv.models import PosixDataObject
from omnia.utils import path_exists

help_doc = """
Register a file, from a Posix filesystem, into Omnia.
It will reload all attributes from the database, if the document has been saved before.
By default, file details are recomputed if the document is accessible.
"""


def make_parser(parser):
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        metavar="PATH",
        help="Path to the file to register",
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Hostname of the registered file",
    )
    parser.add_argument(
        "-c",
        "--compute",
        dest="compute",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Compute file details",
    )
    parser.add_argument(
        "--cs" "--collections",
        dest="cs",
        nargs="+",
        help="Document belongs to this collections",
    )
    parser.add_argument("--tags", nargs="+", help="Tags of the document")


def implementation(logger, args):
    mec = get_mec(args)
    dobj = PosixDataObject(
        logger=logger, mec=mec, path=args.path, host=args.host
    )
    dobj.reload()
    if path_exists(args.path) and args.compute:
        dobj.compute()
    dobj.collections = args.cs
    dobj.tags = args.tags
    dobj.save()


def do_register(registration_list):
    registration_list.append(("reg", help_doc, make_parser, implementation))

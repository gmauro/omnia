import argparse

from omnia.cli import get_mec
from omnia.dv.models import PosixDataObject
from omnia.utils import path_exists

help_doc = """
Register a file, from a Posix filesystem, into Omnia
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
        "-c",
        "--compute",
        dest="compute",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Compute file details",
    )


def implementation(logger, args):
    mec = get_mec(args)
    dobj = PosixDataObject(logger=logger, mec=mec, path=args.path)
    if path_exists(args.path) and args.compute:
        dobj.compute()
    dobj.save()


def do_register(registration_list):
    registration_list.append(("reg", help_doc, make_parser, implementation))

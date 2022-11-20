from omnia.cli import get_mec
from omnia.dv.models import PosixDataObject

help_doc = """
Delete a PosixDataObject document from Omnia
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
    mec = get_mec(args)
    dobj = PosixDataObject(
        logger=logger, mec=mec, path=args.path, host=args.host
    )
    dobj.delete()


def do_register(registration_list):
    registration_list.append(("del", help_doc, make_parser, implementation))

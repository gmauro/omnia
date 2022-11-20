import argparse
import pathlib
from importlib import import_module

from comoda import LOG_LEVELS, a_logger, ensure_dir

from omnia import __appname__, __version__, log_file

SUBMODULES_NAMES = ["omnia.cli.info", "omnia.cli.reg"]
SUBMODULES = [import_module(n) for n in SUBMODULES_NAMES]


class App:
    def __init__(self):
        self.supported_submodules = []
        for m in SUBMODULES:
            m.do_register(self.supported_submodules)

    def make_parser(self):
        example_text = """examples:

         omnia --version
         omnia info"""
        parser = argparse.ArgumentParser(
            prog=__appname__,
            description="Omnia",
            epilog=example_text,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--logfile", type=str, metavar="PATH", help="log file", default=log_file
        )
        parser.add_argument(
            "--loglevel",
            type=str,
            help="logger level.",
            choices=LOG_LEVELS,
            default="INFO",
        )
        parser.add_argument(
            "-v",
            "--version",
            action="version",
            version="%(prog)s {}".format(__version__),
        )

        subparsers = parser.add_subparsers(
            dest="subparser_name",
            title="subcommands",
            description="valid subcommands",
            help="sub-command description",
        )

        for k, h, addarg, impl in self.supported_submodules:
            subparser = subparsers.add_parser(k, help=h)
            addarg(subparser)
            subparser.set_defaults(func=impl)

        return parser


def main():
    app = App()
    parser = app.make_parser()
    args = parser.parse_args()
    log_format = (
        "%(asctime)s|%(levelname)-8s|%(name)s |%(module)s |%(funcName)s |%(message)s"
    )
    if args.logfile == "stdout":
        logger = a_logger("Main", log_format=log_format, level=args.loglevel)
    else:
        logfile = args.logfile
        ensure_dir(pathlib.Path(logfile).parent)
        print("Check logs at {}".format(logfile))
        logger = a_logger(
            "Main", log_format=log_format, level=args.loglevel, filename=logfile
        )

    logger.info("{} started".format(__appname__.capitalize()))
    args.func(logger, args) if hasattr(args, "func") else parser.print_help()
    logger.info("{} ended".format(__appname__.capitalize()))


if __name__ == "__main__":
    main()

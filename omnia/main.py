import argparse
import pathlib
from importlib import import_module

from comoda import LOG_LEVELS, a_logger, ensure_dir

from omnia import __appname__, __version__, log_file
from omnia.config_manager import ConfigurationManager

SUBMODULES_NAMES = {
    "info": ["omnia.cli.info"],
    "dv": ["omnia.cli.del", "omnia.cli.reg"],
}


class App:
    def __init__(self, parser, module):
        self.parser = parser
        self.supported_submodules = []
        submodules = [import_module(n) for n in SUBMODULES_NAMES[module]]
        for m in submodules:
            m.do_register(self.supported_submodules)

    def make_subparser(self):
        subparsers = self.parser.add_subparsers(
            dest="subparser_name",
            title="subcommands",
            description="valid subcommands",
            help="sub-command description",
        )

        for k, h, addarg, impl in self.supported_submodules:
            subparser = subparsers.add_parser(k, help=h)
            addarg(subparser)
            subparser.set_defaults(func=impl)

        return self.parser


def make_parser():
    example_text = """examples:

     omnia --version
     omnia info show"""
    parser = argparse.ArgumentParser(
        prog=__appname__,
        description="Omnia",
        epilog=example_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--configuration_file",
        type=str,
        metavar="PATH",
        help="Configuration file",
    )
    parser.add_argument(
        "module",
        type=str,
        help="Module to load",
        choices=SUBMODULES_NAMES.keys(),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s {}".format(__version__),
    )
    logger_group = parser.add_argument_group("logger")
    logger_group.add_argument(
        "--logfile", type=str, metavar="PATH", help="log file", default=log_file
    )
    logger_group.add_argument(
        "--loglevel",
        type=str,
        help="logger level.",
        choices=LOG_LEVELS,
        default="INFO",
    )
    mongodb_group = parser.add_argument_group("MongoDB")
    mongodb_group.add_argument(
        "--alias",
        type=str,
        help="Alias name for the connection throughout MongoEngine",
    )
    mongodb_group.add_argument(
        "--user",
        type=str,
        help="Username for the connection throughout MongoEngine",
    )
    mongodb_group.add_argument(
        "--password",
        type=str,
        help="Password for the connection throughout MongoEngine",
    )
    mongodb_group.add_argument(
        "--hostname",
        type=str,
        help="Hostname for the connection throughout MongoEngine",
    )

    return parser


# https://towardsdatascience.com/dynamically-add-arguments-to-argparse-python-patterns-a439121abc39
def main():
    parser = make_parser()
    args_, _ = parser.parse_known_args()
    cm = ConfigurationManager(args=args_)

    args_.log_level = cm.get_loglevel
    log_format = cm.get_logformat

    if args_.logfile == "stdout":
        logger = a_logger("Main", log_format=log_format, level=args_.loglevel)
    else:
        logfile = args_.logfile
        ensure_dir(pathlib.Path(logfile).parent)
        print("Check logs at {}".format(logfile))
        logger = a_logger(
            "Main",
            log_format=log_format,
            level=args_.loglevel,
            filename=logfile,
        )

    app = App(parser, args_.module)
    app.make_subparser()
    args = parser.parse_args()

    if args.alias is None:
        args.alias = cm.get_mdbc_alias

    if args.user is None:
        args.user = cm.get_mdbc_username

    if args.password is None:
        args.password = cm.get_mdbc_password

    if args.hostname is None:
        args.hostname = cm.get_mdbc_hostname

    logger.info("{} started".format(__appname__.capitalize()))
    args.func(logger, args) if hasattr(args, "func") else parser.print_help()
    logger.info("{} ended".format(__appname__.capitalize()))


if __name__ == "__main__":
    main()

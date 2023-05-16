import click
import cloup

from omnia import __appname__, __version__, context_settings, log_file, logger
from omnia.config_manager import ConfigurationManager
from omnia.ids.cli.group import did
from omnia.info.group import info


@cloup.group(name="main", help="Omnia", no_args_is_help=True, context_settings=context_settings)
@click.version_option(version=__version__)
@cloup.option("-c", "--configuration_file", help="Configuration file.")
@cloup.option("-q", "--quiet", default=False, is_flag=True, help="Set log verbosity")
@cloup.option_group(
    "MongoDB options",
    cloup.option("--db", help="DB's label."),
    cloup.option("--uri", help="URI string for the connection to the MongoDB server."),
)
@click.pass_context
def cli(ctx, configuration_file, quiet, db, uri):
    if quiet:
        logger.add(log_file, level="INFO", rotation="13:00")
    else:
        logger.add(log_file, level="DEBUG", rotation="13:00")
    logger.info("{} started".format(__appname__.capitalize()))
    ctx.obj = ConfigurationManager(cf=configuration_file, db=db, uri=uri)
    pass


def main():
    cli.add_command(did)
    cli.add_command(info)
    logger.remove()
    cli()


if __name__ == "__main__":
    main()

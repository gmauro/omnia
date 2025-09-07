import sys

import click
import cloup

from omnia import __appname__, __version__, context_settings, log_file, logger
from omnia.cli import (
    add_collection,
    dataset_delete,
    dataset_registration,
    dataset_retrieval,
    delete_collection,
    edit_collection,
    info,
    list_metadata,
    serve,
)
from omnia.config.config_manager import ConfigurationManager


def configure_logging(stdout, verbosity, _logger):
    """
    Configure logging behavior based on stdout flag and verbosity level.

    Args:
        stdout (bool): Flag indicating whether to log to stdout or not.
        verbosity (str): Level of verbosity, can be 'quiet', 'normal' or 'loud'.
        _logger: Logger instance to configure.

    Returns:
        None

    Notes:
        This function configures the logging behavior based on the provided parameters.
        It sets the log level and output target accordingly. If stdout is True,
        logs are written to stdout, otherwise they are written to a file at `log_file`.
        The verbosity parameter determines the log level as follows:
            - 'quiet': Log level set to ERROR
            - 'normal': Log level set to INFO
            - 'loud': Log level set to DEBUG

    """
    target = sys.stdout if stdout else log_file
    loglevel = {"quiet": "ERROR", "normal": "INFO", "loud": "DEBUG"}.get(verbosity, "INFO")

    kwargs = {"level": loglevel}
    if target == sys.stdout:
        fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <yellow>{level: <8}</yellow> | <level>{message}</level>"
        kwargs["format"] = fmt
    else:
        kwargs["retention"] = "30 days"
    _logger.add(target, **kwargs)


@cloup.group(
    name="omnia", show_subcommand_aliases=True, help="Omnia", no_args_is_help=True, context_settings=context_settings
)
@click.version_option(version=__version__)
@cloup.option("--verbosity", type=click.Choice(["quiet", "normal", "loud"]), default="normal", help="Set log verbosity")
@cloup.option("--stdout", is_flag=True, default=False, help="Print logs to the stdout")
@cloup.option("--configuration_file", help="Configuration file.")
@cloup.option_group(
    "MongoDB options",
    cloup.option("--mongo-uri", help="URI connection string to reach the MongoDB server."),
    cloup.option("--mongo-profile", help="Profile to retrieve from the configuration file for the MongoDB connection."),
)
def cli(verbosity, stdout, configuration_file, mongo_uri, mongo_profile):
    configure_logging(stdout, verbosity, logger)
    logger.info(f"{__appname__.capitalize()} started")

    # Initialize the ConfigurationManager
    ConfigurationManager(cf=configuration_file, uri=mongo_uri, profile=mongo_profile)


def main():
    cli.section("Collections", add_collection, edit_collection, delete_collection)
    cli.section("Datasets", dataset_retrieval, dataset_registration, dataset_delete)
    cli.section("Metadata", list_metadata)
    cli.add_command(info)
    cli.add_command(serve)
    logger.remove()
    cli()


if __name__ == "__main__":
    main()

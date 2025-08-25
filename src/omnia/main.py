import sys

import click
import cloup

from omnia import __appname__, __version__, context_settings, log_file, logger
from omnia.cli import co, info, list_metadata, reg, serve
from omnia.config.config_manager import ConfigurationManager
from omnia.mongo.mongo_manager import mongo_deployment_types


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


@cloup.group(name="main", help="Omnia", no_args_is_help=True, context_settings=context_settings)
@click.version_option(version=__version__)
@cloup.option("--verbosity", type=click.Choice(["quiet", "normal", "loud"]), default="normal", help="Set log verbosity")
@cloup.option("--stdout", is_flag=True, default=False, help="Print logs to the stdout")
@cloup.option("--configuration_file", help="Configuration file.")
@cloup.option_group(
    "MongoDB options",
    cloup.option("--mongo-uri", help="URI connection string to reach the MongoDB server."),
    cloup.option(
        "--mongo-deployment",
        type=click.Choice(mongo_deployment_types),
        default="embedded",
        help="Specify the deployment environment for the MongoDB server",
    ),
)
@click.pass_context
def cli(ctx, verbosity, stdout, configuration_file, mongo_uri, mongo_deployment):
    configure_logging(stdout, verbosity, logger)
    logger.info(f"{__appname__.capitalize()} started")

    ctx.ensure_object(dict)
    ctx.obj["mongo"] = {"uri": mongo_uri, "deployment": mongo_deployment}

    # Initialize the ConfigurationManager
    ConfigurationManager(cf=configuration_file, uri=mongo_uri)


def main():
    cli.add_command(info)
    cli.add_command(co)
    cli.add_command(reg)
    cli.add_command(serve)
    cli.add_command(list_metadata)
    logger.remove()
    cli(obj={})


if __name__ == "__main__":
    main()

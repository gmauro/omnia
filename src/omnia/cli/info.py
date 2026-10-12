import click
import cloup

from omnia import __appname__, __version__, data_dir, log_file
from omnia.config.config_manager import ConfigurationManager

help_doc = """
Show Omnia details
"""


@cloup.command("info", no_args_is_help=False, help=help_doc)
@click.pass_context
def info(ctx):
    print(f"{__appname__.capitalize()}, version {__version__}\n")

    config = ConfigurationManager()
    paths = {"log file": log_file, "data dir": data_dir, "config file": config.config_file}
    print("Paths: ")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    print("\n")

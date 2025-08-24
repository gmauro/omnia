import click
import cloup

from omnia import __appname__, __version__, config_dir, data_dir, log_file

help_doc = """
Show Omnia details
"""


@cloup.command("info", no_args_is_help=False, help=help_doc)
@click.pass_context
def info(ctx):
    print(f"{__appname__.capitalize()}, version {__version__}\n")

    paths = {"log file": log_file, "data dir": data_dir, "config dir": config_dir}
    print("Paths: ")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    print("\n")

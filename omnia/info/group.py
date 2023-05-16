import cloup

from omnia import __appname__, __version__, config_dir, log_file

help_doc = """
Show Omnia details
"""


@cloup.command("info", no_args_is_help=False, help=help_doc)
def info():
    print("{}, version {}\n".format(__appname__.capitalize(), __version__))

    omnia_paths = {"log file": log_file, "config dir": config_dir}
    print("Paths: ")
    for k, v in omnia_paths.items():
        print("  {}: {}".format(k, v))
    print("\n")

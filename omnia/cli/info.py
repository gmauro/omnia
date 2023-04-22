from omnia import __appname__, __version__, config_dir, log_file

help_doc = """
Show Omnia details
"""


def make_parser(parser):
    ...


def implementation(logger, args):
    print("{} {}\n".format(__appname__.capitalize(), __version__))

    omnia_paths = {"log file": log_file, "config dir": config_dir}
    print("Paths: ")
    for k, v in omnia_paths.items():
        print("  {}: {}".format(k, v))
    print("\n")


def do_register(registration_list):
    registration_list.append(("show", help_doc, make_parser, implementation))

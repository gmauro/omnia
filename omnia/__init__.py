"""Read details from files."""

import os.path
from appdirs import user_log_dir

here = os.path.abspath(os.path.dirname(__file__))
__all__ = ["__appname__", "__version__", "log_file"]

with open(os.path.join(os.path.dirname(here), "omnia", "APPNAME")) as app_file:
    __appname__ = app_file.read().strip()

with open(os.path.join(os.path.dirname(here), "omnia", "VERSION")) as version_file:
    __version__ = version_file.read().strip()

log_file = user_log_dir(__appname__)

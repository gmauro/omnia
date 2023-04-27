"""Read details from files."""

import importlib.metadata
import os.path

from appdirs import user_config_dir, user_log_dir

here = os.path.abspath(os.path.dirname(__file__))
__all__ = ["__appname__", "__version__", "config_dir", "log_file"]

__appname__ = __name__

__version__ = importlib.metadata.version(__appname__)

log_file = user_log_dir(__appname__)
config_dir = user_config_dir(__appname__)

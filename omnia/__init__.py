"""Read details from files."""

import importlib.metadata
import os.path

from appdirs import user_config_dir, user_log_dir
from cloup import Context, HelpFormatter, HelpTheme, Style
from loguru import logger as a_logger

here = os.path.abspath(os.path.dirname(__file__))
__all__ = ["__appname__", "__version__", "config_dir", "log_file", "config_filename", "context_settings", "logger"]

__appname__ = __name__

__version__ = importlib.metadata.version(__appname__)

log_file = user_log_dir(__appname__)
config_dir = user_config_dir(__appname__)

config_filename = "config.yaml"

# Check the docs for all available arguments of HelpFormatter and HelpTheme.
formatter_settings = HelpFormatter.settings(
    theme=HelpTheme(
        invoked_command=Style(fg="red"),
        heading=Style(fg="bright_white", bold=True),
        constraint=Style(fg="magenta"),
        col1=Style(fg="yellow"),
    )
)

context_settings = Context.settings(formatter_settings=formatter_settings)

logger = a_logger
logger.remove()

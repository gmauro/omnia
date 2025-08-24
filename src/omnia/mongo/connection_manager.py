"""
Manager to handle Mongoengine's connection
"""

from mongoengine import connect, disconnect
from pydantic import MongoDsn

DEFAULT_URI = ""


def get_mec(uri=None):
    """Factory function to create a MongoEngineConnectionManager instance."""
    return MongoEngineConnectionManager(uri=uri)


def get_mec_from_config():
    """Factory function to create a MongoEngineConnectionManager instance using config."""
    return MongoEngineConnectionManager()


class MongoEngineConnectionManager:
    """Context manager for handling Mongoengine connections."""

    def __init__(self, uri=None):
        """
        Initialize the connection manager.

        Args:
            uri: MongoDB connection URI. If None, it will try to import from config.
        """
        self.uri = uri if uri is not None else self._get_uri_from_config()

    @staticmethod
    def _get_uri_from_config() -> MongoDsn | str:
        """Helper method to get URI from config or use default."""
        try:
            from ..main import ConfigurationManager

            cm = ConfigurationManager()
            print(cm.get_mdbc_uri)
            return cm.get_mdbc_uri
        except ImportError:
            return DEFAULT_URI

    def __enter__(self):
        """Establish MongoDB connection when entering the context."""
        connect(host=self.uri)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Close MongoDB connection when exiting the context."""
        disconnect()

"""
Manager to handle Mongoengine's connection
"""
from mongoengine import connect, disconnect

from omnia.config_manager import ConfigurationManager


class MongoEngineConnectionManager:
    def __init__(self, **kwargs):
        cm = ConfigurationManager()
        self.alias = kwargs.get("alias", cm.get_mdbc_alias)
        self.db = kwargs.get("db", cm.get_mdbc_db)
        self.username = kwargs.get("username", cm.get_mdbc_username)
        self.password = kwargs.get("password", cm.get_mdbc_password)
        self.host = kwargs.get("host", cm.get_mdbc_hostname)
        self.port = kwargs.get("port", cm.get_mdbc_port)
        self.auth_mech = kwargs.get(
            "authentication_mechanism", cm.get_mdbc_auth_mech
        )
        self.auth_source = kwargs.get(
            "authentication_source", cm.get_mdbc_auth_source
        )

    def __enter__(self):
        connect(
            db=self.db,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            alias=self.alias,
            authentication_mechanism=self.auth_mech,
            authentication_source=self.auth_source,
        )

    def __exit__(self, exc_type, exc_value, exc_traceback):
        disconnect(alias=self.alias)

"""
Manager to handle Mongoengine's connection
"""
from mongoengine import connect, disconnect


class MongoEngineConnectionManager:
    def __init__(self, **kwargs):
        self.alias = kwargs.get("alias", "omnia_dv_alias")
        self.db = kwargs.get("db", "omnia_dv")
        self.username = kwargs.get("username", None)
        self.password = kwargs.get("password", None)
        self.host = kwargs.get("host", None)
        self.port = kwargs.get("port", 27017)
        self.auth_mech = kwargs.get("authentication_mechanism", "SCRAM-SHA-256")
        self.auth_source = kwargs.get("authentication_source", "omnia_dv")

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

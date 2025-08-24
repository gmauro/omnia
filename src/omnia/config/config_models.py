from pydantic import BaseModel, MongoDsn


class MongoDBConfig(BaseModel):
    uri: MongoDsn


class Configuration(BaseModel):
    mdbc: MongoDBConfig

"""
Command-line interface module
"""
from omnia.dv.connection import MongoEngineConnectionManager


def get_mec(args):
    return MongoEngineConnectionManager(
        alias=args.alias,
        username=args.user,
        password=args.password,
        host=args.host,
    )

"""
Command-line interface module
"""
from omnia.dv.connection import MongoEngineConnectionManager


def get_mec(args):
    return MongoEngineConnectionManager(
        db=args.db,
        username=args.username,
        password=args.password,
        host=args.hostname,
        port=args.port,
        auth_mech=args.auth_mech,
        auth_source=args.auth_source,
    )

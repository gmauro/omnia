import json

import click
import cloup

from omnia.cli.commons import is_collection_or_data_object
from omnia.models.data_collection import Datacatalog, DataCollection
from omnia.models.data_object import PosixDataObject
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri
from omnia.utils import Hashing


@cloup.command("ls", aliases=["list"], no_args_is_help=False, help="List metadata of Data Objects, Collections.")
@cloup.argument("source", default=None, required=False, help="Collection's title or Data Object's path")
@cloup.option(
    "-l", "--full-path", is_flag=True, required=False, help="List Data Object full path. It works only for Collections."
)
@cloup.option(
    "-k",
    "--verify-checksums",
    is_flag=True,
    required=False,
    help="Verify Data Object integrity. It works only for Collections.",
)
@click.pass_context
def list_metadata(ctx: click.Context, source, full_path, verify_checksums) -> None:
    """
    List metadata of Data Objects, Collections

    Args:
        ctx: Click context object.
        source: Collection's title or Data Object's path
        verify_checksums: flag to verify checksums of Data Objects. It works only for Collections.
        full_path: flag to list full path of data objects in the collections.
    """
    mongo_uri = get_mongo_uri(ctx)

    hg = Hashing()

    with get_mec(uri=mongo_uri):
        collection, data_object_path, cobj, dojs = is_collection_or_data_object(source)

        if not collection and not data_object_path and source:
            print(f"I couldn't find either a collection or a dataset with the name '{source}'")
            return

        if collection:
            print(f"{cobj.desc} collection")
            print("-" * len(cobj.desc))

            for field_name in cobj.mdb_obj._fields.keys():
                field_value = cobj.mdb_obj[field_name]
                if field_name not in ("name", "id", "uk", "context", "type") + Datacatalog.json_dict_fields():
                    print(f"  - {field_name}: {field_value}")
                if field_name in Datacatalog.json_dict_fields():
                    if field_value:
                        print(f"  - {field_name}:")
                        field_value = json.loads(field_value)
                        for subk, v in field_value.items():
                            print(f"      - {subk}: {v}")
                        continue
                    print(f"  - {field_name}: {field_value}")
            print(f"  - objects: {len(PosixDataObject().query(included_in_datacatalog=cobj.mdb_obj))}")

            if full_path or verify_checksums:
                dojs = PosixDataObject().query(included_in_datacatalog=cobj.mdb_obj)
                for pdo in dojs:
                    formatted_string = f"    - {pdo['path']}"
                    if verify_checksums:
                        ck = hg.compute_file_hash(pdo["path"]) == pdo["checksum"]
                        formatted_string = f"    - {ck} {pdo['path']}"
                    print(formatted_string)
            return

        if data_object_path:
            for pdo in dojs:
                if verify_checksums:
                    ck = hg.compute_file_hash(pdo["path"]) == pdo["checksum"]
                    print(f"  - checksum verified: {ck}")
                for field_name, field_value in pdo.items():
                    if field_name not in ("_cls", "_id", "uk", "context", "type"):
                        if field_name == "included_in_datacatalog":
                            collection_names = []
                            for coll_id in field_value:
                                coll = DataCollection(pk=coll_id).map()
                                collection_names.append(coll.desc)
                            print(f"  - {field_name}: {collection_names}")
                            continue
                        print(f"  - {field_name}: {field_value}")
            return

        collections = Datacatalog.objects()
        if not collections:
            print("No collections found in the database.")
            return

        print(f"\nCollections in the database: {len(collections)}")
        print("=" * 40)

        for coll in collections:
            print(f"- {coll.name}")

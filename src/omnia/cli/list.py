import json

import cloup

from omnia.cli.commons import is_collection_or_data_object
from omnia.models.data_collection import Datacatalog, DataCollection
from omnia.models.data_object import PosixDataObject
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri
from omnia.utils import Hashing


@cloup.command("ls", aliases=["list"], no_args_is_help=False, help="Legacy: list metadata of datasets and catalogues.")
@cloup.argument("source", default=None, required=False, help="Catalogue title or dataset path")
@cloup.option(
    "-l", "--full-path", is_flag=True, required=False, help="List dataset full paths. Works only for catalogues."
)
@cloup.option(
    "-k",
    "--verify-checksums",
    is_flag=True,
    required=False,
    help="Verify dataset integrity. Works only for catalogues.",
)
def list_metadata(source, full_path, verify_checksums) -> None:
    """
    List metadata of datasets and catalogues.

    Args:
        source: Catalogue title or dataset path.
        verify_checksums: Verify dataset checksums; works only for catalogues.
        full_path: List dataset paths in the catalogue.
    """
    mongo_uri = get_mongo_uri()

    hg = Hashing()

    with get_mec(uri=mongo_uri):
        collection, data_object_path, cobj, dojs = is_collection_or_data_object(source)

        if not collection and not data_object_path and source:
            print(f"I couldn't find either a catalogue or a dataset with the name '{source}'")
            return

        if collection:
            print(f"{cobj.desc} catalogue")
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
            print("No catalogues found in the database.")
            return

        print(f"\nCatalogues in the database: {len(collections)}")
        print("=" * 40)

        for coll in collections:
            print(f"- {coll.name}")

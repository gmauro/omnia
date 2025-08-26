import click
import cloup

from omnia.mongo.connection_manager import get_mec
from omnia.mongo.models import DataCollection, Dataset, PosixDataObject
from omnia.mongo.mongo_manager import embedded_mongo, get_mongo_uri


@cloup.command("ls", aliases=["list"], no_args_is_help=False, help="List metadata of Data Objects, Collections.")
@cloup.option("-c", "--collection", default=None, required=False, help="Collection's title")
@cloup.option("-d", "--data-object-path", default=None, required=False, help="Data Object's path")
@cloup.option(
    "-l", "--full-path", is_flag=True, required=False, help="List Data Object full path. It works only for Collections."
)
@click.pass_context
def list_metadata(ctx: click.Context, collection, data_object_path, full_path) -> None:
    """
    List metadata of Data Objects, Collections

    Args:
        ctx: Click context object.
        collection: title for the collection.
        data_object_path: path for the data object.
        full_path: flag to list full path of data objects in the collections.
    """
    with embedded_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)

        with get_mec(uri=mongo_uri):
            collections = Dataset.objects()
            if collection:
                _collection = collections.filter(title=collection).first()
                print(f"{_collection['title']} collection")
                print("-" * len(_collection["title"]))
                for field_name in _collection._fields.keys():
                    if field_name not in ("title", "id"):
                        print(f"  - {field_name}: {_collection[field_name]}")
                print(f"  - objects: {len(PosixDataObject(uri=mongo_uri).query(collections=_collection))}")
                if full_path:
                    dojs = PosixDataObject(uri=mongo_uri).query(collections=_collection)
                    for do in dojs:
                        print(f"    - {do['path']}")
                return
            if data_object_path:
                dojs = PosixDataObject(uri=mongo_uri).query(path=data_object_path)

                if not dojs:
                    print(f"Data object '{data_object_path}' not found.")
                    return
                for pdo in dojs:
                    for field_name, field_value in pdo.items():
                        if field_name not in ("_cls", "_id"):
                            if field_name == "collections":
                                collection_names = []
                                for coll_id in field_value:
                                    for coll in DataCollection(uri=mongo_uri).query(id=coll_id):
                                        collection_names.append(coll["title"])
                                print(f"  - {field_name}: {collection_names}")
                                continue
                            print(f"  - {field_name}: {field_value}")
                return

            if not collections:
                print("No collections found in the database.")
                return

            print(f"\nCollections in the database: {len(collections)}")
            print("=" * 40)

            for coll in collections:
                print(f"- {coll['title']}")

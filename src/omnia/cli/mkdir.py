import cloup

from omnia.cli.commons import get_data_collection
from omnia.models.data_collection import DataCollection
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri


@cloup.command("mkdir", aliases=["mkcoll"], no_args_is_help=True, help="Create a new collection in the database.")
@cloup.argument("name", help="Collection's name", required=True)
@cloup.option("--description", help="Collection's description")
@cloup.option("--keywords", help="Collection's keywords", multiple=True)
def add_collection(name: str, description: str = None, keywords: list = None) -> None:
    """
    Add a collection to the database if it doesn't exist.
    If it exists, display its details.

    Args:
        name: name for the collection.
        description: Description for the collection.
        keywords: Keywords for the collection.
    """
    mongo_uri = get_mongo_uri()

    collection_data = {
        "name": name,
        "description": description,
        "keywords": keywords,
    }

    with get_mec(uri=mongo_uri):
        collection = get_data_collection(name)
        if not collection:
            collection = DataCollection(**collection_data)
            collection.save()
        else:
            print(f"Collection {name} already exists.")
            return

    # Print the name as the main title
    print(f"\n{'=' * 40}")
    print(f"{collection.mdb_obj.name} collection")
    print(f"{'=' * 40}")

    # Print the other fields in a list format
    for field_name in collection.mdb_obj._fields.keys():
        if field_name not in ("name", "id", "uk"):  # Skip the name as it's already printed
            print(f"  - {field_name}: {collection.mdb_obj[field_name]}")

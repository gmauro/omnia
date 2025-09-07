import cloup

from omnia.cli.commons import get_data_collection
from omnia.models.data_object import PosixDataObject
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri


@cloup.command("rmdir", aliases=["rmcoll"], no_args_is_help=True, help="Delete a collection from the database.")
@cloup.argument("name", help="Collection's name", required=True)
def delete_collection(name: str) -> None:
    """
    Delete a collection from the database.

    Args:
        name: name for the collection.
    """
    mongo_uri = get_mongo_uri()

    with get_mec(uri=mongo_uri):
        collection = get_data_collection(name)

        if not collection:
            print(f"Collection '{name}' not found.")
            return

        dojs = PosixDataObject().query(included_in_datacatalog=collection.mdb_obj)
        if dojs:
            verb = "is" if len(dojs) == 1 else "are"
            print(f"{len(dojs)} data object(s) {verb} still referenced by this collection. Use rm")
        else:
            collection.delete()
            print(f"Collection '{name}' deleted successfully.")

import json

import cloup

from omnia.cli.commons import get_data_collection
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri


@cloup.command("mv", aliases=["edit"], no_args_is_help=True, help="Edit a collection in the database.")
@cloup.argument("name", help="Collection's current name", required=True)
@cloup.argument("new-name", help="Collection's new name", required=False)
@cloup.option("-d", "--description", help="New description for the collection")
@cloup.option("--keywords", help="New keywords for the collection", multiple=True)
@cloup.option("--notes", help="New notes for the collection")
def edit_collection(name: str, new_name: str, description: str, keywords: list[str], notes: str) -> None:
    """
    Edit collection's details in the database.
    """
    mongo_uri = get_mongo_uri()

    with get_mec(uri=mongo_uri):
        collection = get_data_collection(name)
        if not collection:
            print(f"Collection '{name}' not found.")
            return

        if new_name:
            collection.mdb_obj.title = new_name
            collection.update()
            print(f"Collection '{name}' renamed to '{new_name}'.")

        touched = False
        if description is not None:
            collection.mdb_obj.description = description
            touched = True
        if len(keywords) > 0:
            collection.mdb_obj.keywords = keywords
            touched = True
        if notes is not None:
            try:
                json.loads(notes)
                collection.mdb_obj.notes = notes
                touched = True
            except json.JSONDecodeError:
                print('Invalid JSON format for notes. It should be like this: \'{"key": "value"}\'. Notes not updated.')

        if not touched:
            print(f"Collection '{collection.desc}' unchanged. No changes made.")
            return

        collection.update()
        print(f"Collection '{collection.desc}' updated successfully.")

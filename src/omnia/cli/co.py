import json

import click
import cloup

from omnia.models.data_collection import DataCollection
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import embedded_mongo, get_mongo_uri

HELP_DOC = "Manage collections in the database."


@cloup.command("edit", aliases=["mv"], no_args_is_help=True, help="Edit a collection in the database.")
@cloup.argument("title", help="Collection's current title", required=True)
@cloup.argument("new-title", help="Collection's new title", required=False)
@cloup.option("-d", "--description", help="New description for the collection")
@cloup.option("--tags", help="New tags for the collection", multiple=True)
@cloup.option("--notes", help="New notes for the collection")
@click.pass_context
def edit_collection(
    ctx: click.Context, title: str, new_title: str, description: str, tags: list[str], notes: str
) -> None:
    """
    Edit collection's details in the database.
    """
    with embedded_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)

        with get_mec(uri=mongo_uri):
            collection = DataCollection(title=title).map()
            if not collection:
                print(f"Collection '{title}' not found.")
                return

            if new_title:
                collection.mdb_obj.title = new_title
                collection.update()
                print(f"Collection '{title}' renamed to '{new_title}'.")

            touched = False
            if description is not None:
                collection.mdb_obj.description = description
                touched = True
            if len(tags) > 0:
                collection.mdb_obj.tags = tags
                touched = True
            if notes is not None:
                try:
                    json.loads(notes)
                    collection.mdb_obj.notes = notes
                    touched = True
                except json.JSONDecodeError:
                    print(
                        'Invalid JSON format for notes. It should be like this: \'{"key": "value"}\'. '
                        "Notes not updated."
                    )

            if not touched:
                print(f"Collection '{collection.desc}' unchanged. No changes made.")
                return

            collection.update()
            print(f"Collection '{collection.desc}' updated successfully.")


@cloup.command("mkcoll", aliases=["mkdir"], no_args_is_help=True, help="Create a new collection in the database.")
@cloup.argument("title", help="Collection's title", required=True)
@cloup.option("--description", help="Collection's description")
@cloup.option("--tags", help="Collection's tags", multiple=True)
@click.pass_context
def add_collection(ctx: click.Context, title: str, description: str = None, tags: list = None) -> None:
    """
    Add a collection to the database if it doesn't exist.
    If it exists, display its details.

    Args:
        ctx: Click context object.
        title: title for the collection.
        description: Description for the collection.
        tags: Tags for the collection.
    """
    with embedded_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)

        collection_data = {
            "title": title,
            "description": description,
            "tags": tags,
        }

        with get_mec(uri=mongo_uri):
            collection = DataCollection(uri=mongo_uri, **collection_data)
            collection.save()

    # Print the title as the main title
    print(f"\n{'=' * 40}")
    print(f"{collection.mdb_obj['title']} collection")
    print(f"{'=' * 40}")

    # Print the other fields in a list format
    for field_name in collection.mdb_obj._fields.keys():
        if field_name not in ("title", "id", "uk"):  # Skip the title as it's already printed
            print(f"  - {field_name}: {collection.mdb_obj[field_name]}")


@cloup.command("rmcoll", aliases=["rmdir"], help="Delete a collection from the database.")
@cloup.argument("title", help="Collection's title", required=True)
@click.pass_context
def delete_collection(ctx: click.Context, title: str) -> None:
    """
    Delete a collection from the database.

    Args:
        ctx: Click context object.
        title: title for the collection.
    """
    with embedded_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)

        with get_mec(uri=mongo_uri):
            collection = DataCollection(uri=mongo_uri, title=title).map()

            if not collection:
                print(f"Collection with title '{title}' not found.")
                return

            collection.delete()

    print(f"Collection '{title}' deleted successfully.")

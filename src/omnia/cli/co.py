import click
import cloup

from omnia.mongo.models import DataCollection
from omnia.mongo.mongo_manager import embedded_mongo, get_mongo_uri

HELP_DOC = "Manage collections in the database."


@cloup.group("co", no_args_is_help=True, help=HELP_DOC)
def co():
    """Manage collections in the database."""
    pass


@co.command("add", no_args_is_help=True, help="Add a new collection to the database.")
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

        collection = DataCollection(uri=mongo_uri, **collection_data)
        collection.save()

    # Print the title as the main title
    print(f"\n{'=' * 40}")
    print(f"{collection.mdb_obj['title']} collection")
    print(f"{'=' * 40}")

    # Print the other fields in a list format
    for field_name in collection.mdb_obj._fields.keys():
        if field_name not in ("title", "id"):  # Skip the title as it's already printed
            print(f"  - {field_name}: {collection.mdb_obj[field_name]}")


@co.command("ed", aliases=["edit"], no_args_is_help=True, help="Edit an existing collection in the database.")
@cloup.argument("title", help="Collection's title", required=True)
@cloup.option("-d", "--description", help="New description for the collection")
@cloup.option("--tags", help="New tags for the collection", multiple=True)
@click.pass_context
def edit_collection(ctx: click.Context, title: str, description: str = None, tags: list = None) -> None:
    """
    Edit an existing collection in the database.

    Args:
        ctx: Click context object.
        title: title for the collection.
        description: New description for the collection.
        tags: New tags for the collection.
    """
    with embedded_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)

        collection = DataCollection(uri=mongo_uri, title=title).map()
        if not collection:
            print(f"Collection with title '{title}' not found.")
            return

        if description is not None:
            collection.mdb_obj.description = description
        if tags is not None:
            collection.mdb_obj.tags = tags

        collection.save(force_update=True)

    print(f"Collection '{title}' updated successfully.")


@co.command("del", aliases=["delete"], help="Delete a collection from the database.")
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

        collection = DataCollection(uri=mongo_uri, title=title).map()

        if not collection:
            print(f"Collection with title '{title}' not found.")
            return

        collection.delete()

    print(f"Collection '{title}' deleted successfully.")

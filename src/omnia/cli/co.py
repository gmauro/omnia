import click
import cloup

from omnia.mongo.connection_manager import get_mec
from omnia.mongo.models import DataCollection, Dataset, PosixDataObject
from omnia.mongo.mongo_manager import get_mongo_uri, manage_mongo

HELP_DOC = "Manage collections in the database."


@cloup.group("co", no_args_is_help=True, help=HELP_DOC)
def co():
    """Manage collections in the database."""
    pass


@co.command("add", no_args_is_help=True, help="Add a new collection to the database.")
@cloup.option("--label", help="Collection's label", required=True)
@cloup.option("--description", help="Collection's description")
@cloup.option("--ext-uid", help="Collection's external UID")
@cloup.option("--tags", help="Collection's tags", multiple=True)
@click.pass_context
def add_collection(
    ctx: click.Context, label: str, description: str = None, ext_uid: str = None, tags: list = None
) -> None:
    """
    Add a collection to the database if it doesn't exist.
    If it exists, display its details.

    Args:
        ctx: Click context object.
        label: Label for the collection.
        description: Description for the collection.
        ext_uid: External UID for the collection.
        tags: Tags for the collection.
    """
    with manage_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)

        collection_data = {
            "title": label,
            "description": description,
            "ext_uid": ext_uid,
            "tags": tags,
        }

        collection = Dataset(uri=mongo_uri, **collection_data)
        collection.save()
        import time

        time.sleep(30)  # Wait

    # Print the title as the main title
    print(f"\n{'=' * 40}")
    print(f"{collection.mdb_obj['title']} collection")
    print(f"{'=' * 40}")

    # Print the other fields in a list format
    for field_name in collection.mdb_obj._fields.keys():
        if field_name not in ("title", "id"):  # Skip the title as it's already printed
            print(f"  - {field_name}: {collection.mdb_obj[field_name]}")


@co.command("ed", aliases=["edit"], help="Edit an existing collection in the database.")
@cloup.option("--label", help="Collection's label", required=True)
@cloup.option("--description", help="New description for the collection")
@cloup.option("--ext-uid", help="New external UID for the collection")
@cloup.option("--tags", help="New tags for the collection", multiple=True)
@click.pass_context
def edit_collection(
    ctx: click.Context, label: str, description: str = None, ext_uid: str = None, tags: list = None
) -> None:
    """
    Edit an existing collection in the database.

    Args:
        ctx: Click context object.
        label: Label for the collection.
        description: New description for the collection.
        ext_uid: New external UID for the collection.
        tags: New tags for the collection.
    """
    with manage_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)

        collection = Dataset(uri=mongo_uri, title=label)
        if not collection:
            print(f"Collection with label '{label}' not found.")
            return

        if description is not None:
            collection.mdb_obj.description = description
        if ext_uid is not None:
            collection.mdb_obj.ext_uid = ext_uid
        if tags is not None:
            collection.mdb_obj.tags = tags

        collection.save(force_update=True)

    print(f"Collection '{label}' updated successfully.")


@co.command("del", aliases=["delete"], help="Delete a collection from the database.")
@cloup.option("--label", help="Collection's label", required=True)
@click.pass_context
def delete_collection(ctx: click.Context, label: str) -> None:
    """
    Delete a collection from the database.

    Args:
        ctx: Click context object.
        label: Label for the collection.
    """
    with manage_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)

        with get_mec(uri=mongo_uri):
            collection = DataCollection.objects(title=label)

            if not collection:
                print(f"Collection with label '{label}' not found.")
                return

            collection.delete()

    print(f"Collection '{label}' deleted successfully.")


@co.command("ls", aliases=["list"], help="List all collections in the database.")
@click.pass_context
def list_collections(ctx: click.Context) -> None:
    """
    List all collections in the database.

    Args:
        ctx: Click context object.
    """
    with manage_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)

        with get_mec(uri=mongo_uri):
            collections = DataCollection.objects()

            if not collections:
                print("No collections found in the database.")
                return

            print(f"\nCollections in the database: {len(collections)}")
            print("=" * 40)

            for collection in collections:
                print(f"\n{collection['title']} collection")
                print("-" * len(collection["title"]))

                for field_name in collection._fields.keys():
                    if field_name not in ("title", "id"):
                        print(f"  - {field_name}: {collection[field_name]}")
                print(f"  - objects: {len(PosixDataObject(uri=mongo_uri).query(collections=collection))}")

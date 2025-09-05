import click
import cloup

from omnia.cli.commons import get_data_object, get_datacatalog, match_files
from omnia.models.data_object import PosixDataObject
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri

HELP_DOC_REG = """
Register datasets to an Omnia collection.
"""


@cloup.command("reg", no_args_is_help=True, help=HELP_DOC_REG)
@cloup.argument("source", help="Input path")
@cloup.argument("collection-name", help="The collection's name to register files into")
@cloup.option("-k", "--skip-metadata-computation", is_flag=True, help="Skip metadata computation")
@cloup.option("-f", "--force", is_flag=True, help="Force registration without prompting")
@click.pass_context
def dataset_registration(ctx, source, collection_name, skip_metadata_computation, force):
    """Register datasets to an Omnia collection"""

    file_paths = match_files(source)
    if not file_paths:
        print("No files found matching the pattern.")
        return
    print(f"{len(file_paths)} files to register")

    compute_metadata = not skip_metadata_computation

    mongo_uri = get_mongo_uri(ctx)
    with get_mec(uri=mongo_uri):
        datacatalog = get_datacatalog(collection_name)
        if not datacatalog:
            print(f"Datacatalog for collection '{collection_name}' not found.")
            return

        # Print the results
        for file_path in file_paths:
            pdo = get_data_object(file_path)

            if not pdo:
                pdo_data = {
                    "path": str(file_path),
                    "included_in_datacatalog": [datacatalog],
                }
                pdo = PosixDataObject(uri=mongo_uri, **pdo_data)

                if compute_metadata:
                    pdo.compute()
                pdo.save()

            else:
                dc_present = datacatalog in pdo.mdb_obj.included_in_datacatalog
                match (dc_present, force):
                    case (False, _):
                        # https://docs.mongoengine.org/guide/defining-documents.html#many-to-many-with-listfields
                        pdo.update(push__included_in_datacatalog=datacatalog)
                    case (True, True):
                        pdo.compute().update()
                    case (True, False):
                        print(f"File {file_path} already registered. Use --force to overwrite.")


HELP_DOC_GET = """
Get a list of dataset paths from an Omnia collection.
"""


@cloup.command("get", no_args_is_help=True, help=HELP_DOC_GET)
@cloup.argument("collection-name", help="The collection's name")
@click.pass_context
def dataset_retrieval(ctx, collection_name):
    """
    Get a list of dataset paths from an Omnia collection.
    """
    mongo_uri = get_mongo_uri(ctx)

    with get_mec(uri=mongo_uri):
        datacatalog = get_datacatalog(collection_name)

        pdos = PosixDataObject().query(included_in_datacatalog=datacatalog)

        # Open a file in write mode
        filename = f"dataset_paths_from_{datacatalog.name}.txt"
        with open(filename, "w") as file:
            print(f"Retrieving {len(pdos)} paths from {datacatalog.name}...")
            # Iterate over the PosixDataObject instances
            for pdo in pdos:
                # Get the path and write it to the file
                path = pdo.get("path")
                file.write(path + "\n")

        print(f"Paths have been written to {filename}")

import cloup

from omnia.cli.commons import get_datacatalog
from omnia.models.data_object import PosixDataObject
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri

HELP_DOC_GET = """
Get a list of dataset paths from an Omnia collection.
"""


@cloup.command("get", no_args_is_help=True, help=HELP_DOC_GET)
@cloup.argument("name", help="The collection's name")
def dataset_retrieval(name):
    """
    Get a list of dataset paths from an Omnia collection.
    """
    mongo_uri = get_mongo_uri()

    with get_mec(uri=mongo_uri):
        datacatalog = get_datacatalog(name)

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

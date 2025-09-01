import glob

import click
import cloup

from omnia.models.data_collection import DataCollection
from omnia.models.data_object import PosixDataObject
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import embedded_mongo, get_mongo_uri

HELP_DOC = """
Register files to a Omnia collection.
"""


def match_files(search_path: str) -> list[str]:
    """
    Match files using a glob pattern.

    Args:
        search_path: String to search for files.

    Returns:
        List of matching file paths
    """
    # Use glob to find all files matching the pattern recursively
    files = glob.glob(search_path, recursive=True)

    # Sort the files to match the behavior of `ls`
    files.sort()

    return files


@cloup.command("reg", no_args_is_help=True, help=HELP_DOC)
@cloup.argument("source", help="Input path")
@cloup.argument("collection", help="The collection's title to register files into")
@cloup.option("-k", "--skip-metadata-computation", is_flag=True, help="Skip metadata computation")
@cloup.option("-f", "--force", is_flag=True, help="Force registration without prompting")
@click.pass_context
def reg(ctx, source, collection, skip_metadata_computation, force):
    """Register files into Omnia"""

    file_paths = match_files(source)
    if not file_paths:
        print("No files found matching the pattern.")
        return
    print(f"{len(file_paths)} files to register")

    compute_metadata = not skip_metadata_computation

    with embedded_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)
        with get_mec(uri=mongo_uri):
            dataset = DataCollection(title=collection).map()

            if not dataset:
                print(f"Collection with title '{collection}' not found.")
                return
            _collection = dataset.mdb_obj

            # Print the results
            for file_path in file_paths:
                pdo = PosixDataObject(path=file_path).map()

                if not pdo:
                    pdo_data = {
                        "path": str(file_path),
                        "collections": [_collection],
                    }
                    pdo = PosixDataObject(uri=mongo_uri, **pdo_data)

                    if compute_metadata:
                        pdo.compute()
                    pdo.save()

                else:
                    if _collection not in pdo.mdb_obj.collections:
                        pdo.mdb_obj.collections.append(_collection)
                        pdo.update()
                        continue

                    else:
                        if not force:
                            print(f"File {file_path} already registered. Use --force to overwrite.")
                            continue
                        pdo.compute().update()

import fnmatch
import re
import time
from pathlib import Path

import click
import cloup

from omnia.mongo.connection_manager import get_mec
from omnia.mongo.models import DataCollection, Dataset, PosixDataObject
from omnia.mongo.mongo_manager import get_mongo_uri, manage_mongo
from omnia.utils import Hashing

HELP_DOC = """
Register files into Omnia, from a Posix filesystem.
"""


def check_file_existence(file_paths):
    """
    Check if the given file paths exist.

    Parameters:
    file_paths (list): A list of file paths to check.

    Returns:
    dict: A dictionary with file paths as keys and a boolean value indicating existence.
    """
    existence_check = {}
    for file_path in file_paths:
        existence_check[file_path] = file_path.exists()
    return existence_check


def get_file_paths_from_regex(regex_pattern, directory):
    """
    Get file paths from a directory that match a given regex pattern.

    Parameters:
    regex_pattern (str): The regex pattern to match file paths.
    directory (Path): The directory to search for files.

    Returns:
    list: A list of file paths that match the regex pattern.
    """
    file_paths = []
    # rglob is used to recursively search for all files in the directory and its subdirectories
    for file_path in directory.rglob("*"):
        if re.search(regex_pattern, file_path.name):
            file_paths.append(file_path)
    return file_paths


def get_file_paths_from_glob(glob_pattern, directory):
    """
    Get file paths from a directory that match a given glob pattern.

    Parameters:
    glob_pattern (str): The glob pattern to match file paths.
    directory (Path): The directory to search for files.

    Returns:
    list: A list of file paths that match the glob pattern.
    """
    file_paths = []
    # rglob is used to recursively search for all files in the directory and its subdirectories
    for file_path in directory.rglob("*"):
        if fnmatch.fnmatch(file_path.name, glob_pattern):
            file_paths.append(file_path)
    return file_paths


def validate_regex(pattern):
    """
    Validate the regex pattern.

    Parameters:
    pattern (str): The regex pattern to validate.

    Returns:
    bool: True if the pattern is valid, False otherwise.
    """
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def validate_directory(path):
    """
    Validate the directory path.

    Parameters:
    path (str): The directory path to validate.

    Returns:
    bool: True if the path is a valid directory, False otherwise.
    """
    directory = Path(path)
    return directory.exists() and directory.is_dir()


@cloup.command("reg", no_args_is_help=True, help=HELP_DOC)
@cloup.option("-c", "--collection", help="The collection's title to register files into")
@cloup.option("-k", "--skip-metadata-computation", is_flag=True, help="Skip metadata computation")
@cloup.option("--search-path", required=True, help="The path to search for files")
@cloup.option("--pattern", required=True, help="The pattern to match file names (regex or glob)")
@click.pass_context
def reg(ctx, collection, skip_metadata_computation, search_path, pattern):
    """Register files into Omnia"""

    while True:
        if validate_directory(search_path):
            directory = Path(search_path)
            break
        else:
            print("Invalid search path. Please enter a valid directory path.")

    while True:
        if validate_regex(pattern):
            file_paths = get_file_paths_from_regex(pattern, directory)
            break
        elif any(c in pattern for c in ["*", "?", "[", "]"]):
            file_paths = get_file_paths_from_glob(pattern, directory)
            break
        else:
            print("Invalid pattern. Please enter a valid regex or glob pattern.")

    if not file_paths:
        print("No files found matching the pattern.")
        return

        # Check if the found files exist
    existence_check = check_file_existence(file_paths)

    hg = Hashing()
    compute_metadata = {"compute_metadata": not skip_metadata_computation}

    with manage_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)
        print(Dataset(uri=mongo_uri).query(title=collection))
        with get_mec(uri=mongo_uri):
            _collection = DataCollection.objects(title=collection).first()

            if not _collection:
                print(f"Collection with title '{collection}' not found.")
                return

            # Print the results
            for file_path, exists in existence_check.items():
                print(f"File: {file_path} - Exists: {exists}")
                pdo_data = {
                    "collections": [_collection],
                    "description": "Description of the file2",
                    "path": str(file_path),
                    "data_id": hg.compute_hash(fpath=file_path),
                }

                if compute_metadata:
                    PosixDataObject(uri=mongo_uri, **pdo_data).compute().save()
                else:
                    PosixDataObject(uri=mongo_uri, **pdo_data).save()
        time.sleep(60)

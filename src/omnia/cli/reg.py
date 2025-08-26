import fnmatch
import re
from pathlib import Path

import click
import cloup

from omnia.mongo.connection_manager import get_mec
from omnia.mongo.models import DataCollection, PosixDataObject
from omnia.mongo.mongo_manager import embedded_mongo, get_mongo_uri
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


def match_files(directory: Path, pattern: str) -> list[Path]:
    """
    Match files using either regex or glob pattern.

    Args:
        directory: Directory to search
        pattern: Pattern (regex or glob)

    Returns:
        List of matching file paths
    """
    if validate_regex(pattern):
        return get_file_paths_from_regex(pattern, directory)
    elif any(c in pattern for c in ["*", "?", "[", "]"]):
        return get_file_paths_from_glob(pattern, directory)
    else:
        return [Path(pattern)]


def get_file_paths_from_regex(pattern: str, directory: Path) -> list[Path]:
    """Find files matching a regex pattern."""
    return [file_path for file_path in directory.rglob("*") if re.search(pattern, file_path.name)]


def get_file_paths_from_glob(pattern: str, directory: Path) -> list[Path]:
    """Find files matching a glob pattern."""
    return [file_path for file_path in directory.rglob("*") if fnmatch.fnmatch(file_path.name, pattern)]


def validate_regex(pattern: str) -> bool:
    """Validate regex pattern."""
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def validate_directory(path: str | Path) -> bool:
    """Validate directory path."""
    match path:
        case str():
            directory = Path(path)
        case Path():
            directory = path
    return directory.exists() and directory.is_dir()


@cloup.command("reg", no_args_is_help=True, help=HELP_DOC)
@cloup.argument("source", help="Input path")
@cloup.argument("collection", help="The collection's title to register files into")
@cloup.option("-k", "--skip-metadata-computation", is_flag=True, help="Skip metadata computation")
@cloup.option("-f", "--force", is_flag=True, help="Force registration without prompting")
@click.pass_context
def reg(ctx, source, collection, skip_metadata_computation, force):  # , search_path, pattern):
    """Register files into Omnia"""

    directory = Path(source).parent
    file_pattern = Path(source).name

    if not validate_directory(directory):
        print("Invalid search path. Please enter a valid directory path.")
        return

    file_paths = match_files(directory, file_pattern)

    if not file_paths:
        print("No files found matching the pattern.")
        return

        # Check if the found files exist
    existence_check = check_file_existence(file_paths)

    hg = Hashing()
    compute_metadata = not skip_metadata_computation

    with embedded_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)
        with get_mec(uri=mongo_uri):
            dataset = DataCollection(uri=mongo_uri, title=collection).map()
            # with get_mec(uri=mongo_uri):
            #     _collection = DataCollection.objects(title=collection).first()

            if not dataset:
                print(f"Collection with title '{collection}' not found.")
                return
            _collection = dataset.mdb_obj

            # Print the results
            for file_path, exists in existence_check.items():
                if not exists:
                    print(f"File: {file_path} does not exist. Skipping ...")
                    continue
                data_id = hg.compute_hash(fpath=file_path)
                pdo = PosixDataObject(uri=mongo_uri, data_id=data_id).map()

                if not pdo:
                    pdo_data = {
                        "data_id": data_id,
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
                        return

                    else:
                        if not force:
                            print(f"File {file_path} already registered. Use --force to overwrite.")
                            return
                        pdo.compute().update()

import glob
from typing import Any

from omnia.models.data_collection import Datacatalog, DataCollection
from omnia.models.data_object import PosixDataObject


def get_data_collection(name: str) -> DataCollection | None:
    """
    Retrieves a data catalogue based on its name.

    Parameters:
    name (str): The name of the catalogue to retrieve.

    Returns:
    DataCollection: The data catalogue object if found, otherwise None.
    """
    return DataCollection(name=name).map()


def get_datacatalog(name: str) -> Datacatalog | None:
    """
    Retrieves the data catalogue based on its name.

    Parameters:
    name (str): The name of the catalogue to retrieve.

    Returns:
    Datacatalog: The datacatalog object if found, otherwise None.
    """
    dc = get_data_collection(name)

    return dc.mdb_obj if dc else None


def get_data_object(item: str) -> PosixDataObject | None:
    """Get a PosixDataObject by its path."""
    data_object_obj = PosixDataObject(path=item).map()
    return data_object_obj if data_object_obj else None


def get_data_objects(item: str) -> list[dict] | None:
    """Get a PosixDataObject by its path."""
    data_object_obj = PosixDataObject().query(path=item)
    return data_object_obj if data_object_obj else None


def is_collection_or_data_object(
    item: str,
) -> (
    tuple[bool, bool, None, list[Any]]
    | tuple[bool, bool, DataCollection, list[Any]]
    | tuple[bool, bool, None, PosixDataObject | None]
):
    """
    Checks if the given item is a data catalogue or a dataset.

    Parameters:
    item (str): The name or path of the item to check.

    Returns:
    tuple[bool, bool, DataCollection | None, list[PosixDataObject]]:
        A tuple containing:
        - bool: True if the item is a data catalogue, False otherwise.
        - bool: True if the item is a dataset, False otherwise.
        - DataCollection | None: The catalogue object if the item is a catalogue, None otherwise.
        - list[PosixDataObject]: The list of datasets if the item is a dataset, an empty list otherwise.
    """
    if not item:
        return False, False, None, []

    collection_obj = get_data_collection(item)
    if collection_obj:
        return True, False, collection_obj, []

    data_object_obj = get_data_objects(item)
    return False, bool(data_object_obj), None, data_object_obj


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

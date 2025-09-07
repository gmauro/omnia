import cloup

from omnia.cli.commons import get_data_object, match_files
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri

HELP_DOC_RM = """
Delete datasets from an Omnia collection.
"""


@cloup.command("rm", no_args_is_help=True, help=HELP_DOC_RM)
@cloup.argument("source", help="Input path")
def dataset_delete(source):
    """Delete datasets from an Omnia collection"""
    file_paths = match_files(source)
    if not file_paths:
        print("No files found matching the pattern.")
        return
    print(f"{len(file_paths)} files to delete")

    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        for file_path in file_paths:
            pdo = get_data_object(file_path)
            pdo.delete()

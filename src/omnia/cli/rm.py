import click
import cloup

from omnia.cli.commons import get_data_object, match_files
from omnia.models.data_tree import TreeEntry
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri

HELP_DOC_RM = """
Delete datasets from an Omnia catalogue.
"""


@cloup.command("rm", no_args_is_help=True, help=HELP_DOC_RM)
@cloup.argument("source", help="Input path")
def dataset_delete(source):
    """Delete datasets from an Omnia catalogue"""
    file_paths = match_files(source)
    if not file_paths:
        print("No files found matching the pattern.")
        return
    print(f"{len(file_paths)} files to delete")

    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        objects = []
        for file_path in file_paths:
            pdo = get_data_object(file_path)
            if pdo is None:
                raise click.ClickException(f"Dataset is not registered: {file_path}")
            references = list(TreeEntry.objects(dataset=pdo.mdb_obj))
            if references:
                paths = ", ".join(entry.relative_path for entry in references[:5])
                suffix = " (and more)" if len(references) > 5 else ""
                raise click.ClickException(
                    f"Refusing to delete '{file_path}': it is referenced by {len(references)} "
                    f"tree entr{'y' if len(references) == 1 else 'ies'} ({paths}{suffix}). "
                    "Retire or discard the relevant snapshot before deleting the dataset."
                )
            objects.append(pdo)
        for pdo in objects:
            pdo.delete()

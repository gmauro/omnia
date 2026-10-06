import cloup

from omnia.cli.commons import get_data_object, get_datacatalog, match_files
from omnia.models.data_object import PosixDataObject
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri

HELP_DOC_REG = """
Register datasets to an Omnia catalogue.
"""


@cloup.command("reg", no_args_is_help=True, help=HELP_DOC_REG)
@cloup.argument("source", help="Input path")
@cloup.argument("collection-name", metavar="CATALOGUE", help="The catalogue name to register files into")
@cloup.option("-k", "--skip-metadata-computation", is_flag=True, help="Skip metadata computation")
@cloup.option("-f", "--force", is_flag=True, help="Force registration without prompting")
def dataset_registration(source, collection_name, skip_metadata_computation, force):
    """Register datasets to an Omnia catalogue"""

    file_paths = match_files(source)
    if not file_paths:
        print("No files found matching the pattern.")
        return
    print(f"{len(file_paths)} files to register")

    compute_metadata = not skip_metadata_computation

    mongo_uri = get_mongo_uri()
    with get_mec(uri=mongo_uri):
        datacatalog = get_datacatalog(collection_name)
        if not datacatalog:
            print(f"Catalogue '{collection_name}' not found.")
            return

        # Print the results
        for file_path in file_paths:
            pdo = get_data_object(file_path)

            if not pdo:
                pdo_data = {
                    "path": str(file_path),
                    "included_in_datacatalog": [datacatalog],
                }
                pdo = PosixDataObject(**pdo_data)

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

import json

import click
import cloup

from omnia.cli.commons import get_datacatalog
from omnia.models.data_object import PosixDataObject
from omnia.mongo.connection_manager import get_mec
from omnia.mongo.mongo_manager import get_mongo_uri

HELP_DOC_GET = """
Legacy: list raw registered dataset paths from an Omnia catalogue.
"""


@cloup.command("get", no_args_is_help=True, help=HELP_DOC_GET)
@cloup.argument("name", help="The catalogue name")
@cloup.option(
    "-o", "--output", type=click.File("w", encoding="utf-8"), help="Write paths to this file instead of stdout."
)
@cloup.option("--format", "output_format", type=click.Choice(("paths", "json")), default="paths", show_default=True)
def dataset_retrieval(name, output, output_format):
    """
    Legacy command to list raw registered dataset paths from an Omnia catalogue.
    """
    mongo_uri = get_mongo_uri()

    with get_mec(uri=mongo_uri):
        datacatalog = get_datacatalog(name)
        if not datacatalog:
            raise click.ClickException(f"Catalogue '{name}' was not found.")

        pdos = PosixDataObject().query(included_in_datacatalog=datacatalog)
        paths = [pdo["path"] for pdo in pdos]

    if output_format == "json":
        rendered = json.dumps({"catalog": datacatalog.name, "paths": paths}, indent=2) + "\n"
    else:
        rendered = "".join(f"{path}\n" for path in paths)
    if output:
        output.write(rendered)
        click.echo(f"Wrote {len(paths)} paths to {output.name}.", err=True)
    else:
        click.echo(rendered, nl=False)

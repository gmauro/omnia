import click
import cloup
from mongoengine.errors import NotUniqueError

from omnia import logger
from omnia.connection import get_mec
from omnia.ids.models import DataIdentifier, Reference

help_doc = """
Update a Data identifier
"""


@cloup.command("update", no_args_is_help=True, help=help_doc)
@cloup.option("-l", "--label", help="Label to use for the new data identifier", type=click.Choice(["gwas"]))
@cloup.option(
    "-d",
    "--description",
    help="Description of the new data identifier",
)
@cloup.option(
    "-u",
    "--url",
    help="URL of the new data identifier",
)
@cloup.option("-t", "--title", help="Title of the article to be associated with the new data identifiers")
@click.pass_obj
def update(cm, label, description, url, title):
    mec = get_mec(cm.get_mdbc_db, cm.get_mdbc_uri)
    try:
        with mec:
            obj = DataIdentifier.objects(label=label, description=description)[0]
            if title:
                reference = Reference.objects(title=title)[0]
                obj.modify(references=[reference])
                logger.info("{} DataId modified".format(label))
    except NotUniqueError:
        logger.error("Error")

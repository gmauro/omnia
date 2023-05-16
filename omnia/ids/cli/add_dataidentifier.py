import click
import cloup
from mongoengine.errors import NotUniqueError

from omnia import logger
from omnia.connection import get_mec
from omnia.ids.models import DataIdentifier, Reference

help_doc = """
Create a new Data identifier
"""


@cloup.command("create", no_args_is_help=True, help=help_doc)
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
def create(cm, label, description, url, title):
    mec = get_mec(cm.get_mdbc_db, cm.get_mdbc_uri)
    try:
        with mec:
            if title:
                reference = Reference.objects(title=title)[0]
                did = DataIdentifier(label=label, description=description, url=url, references=[reference])
            else:
                did = DataIdentifier(label=label, description=description, url=url)
            did.save()
            logger.info("{} DataId created".format(label))
    except NotUniqueError:
        logger.info("DataId {} already exists. Skipped creation ".format(label))
    print("{}_{}".format(did.label, did.counter))

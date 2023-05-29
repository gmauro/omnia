import click
import cloup
from mongoengine.errors import NotUniqueError

from omnia import logger
from omnia.connection import get_mec
from omnia.ids.models import DataIdentifier, GwasTraitID

help_doc = """
Create a new Data identifier for a phenotypic trait
"""


@cloup.command("add_trait", no_args_is_help=True, help=help_doc)
@cloup.option("-l", "--label", help="Label to use for the new data identifier")
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
def add_trait(cm, label, description, url, title):
    mec = get_mec(cm.get_mdbc_db, cm.get_mdbc_uri)
    try:
        with mec:
            references = []
            if title:
                references = [DataIdentifier.objects(title=title)[0]]
            trait = GwasTraitID(uk=label, description=description, url=url, references=references, mec=mec)
            trait.save()
            logger.info("{} DataId created".format(label))
    except NotUniqueError as e:
        logger.error("DataId {} already exists. Skipped creation ".format(e))
    print("{}".format(trait.uk))

import click
import cloup
from mongoengine.errors import NotUniqueError

from omnia import logger
from omnia.connection import get_mec
from omnia.ids.models import Reference

help_doc = """
Create a new Article object
"""


@cloup.command("add_article", no_args_is_help=True, help=help_doc)
@cloup.option("-t", "--title", help="Article title")
@cloup.option(
    "-d",
    "--description",
    help="Article description",
)
@cloup.option(
    "--url",
    help="Article URL",
)
@cloup.option("--uid", help="Article unique id e.g.: doi:... pmid:...")
@click.pass_obj
def add_article(cm, title, description, url, uid):
    mec = get_mec(cm.get_mdbc_db, cm.get_mdbc_uri)
    try:
        with mec:
            article = Reference(title=title, description=description, url=url, uid=uid)
            article.save()
            logger.info("{} article created".format(title))
    except NotUniqueError:
        logger.info("Article {} already exists. Skipped creation ".format(title))

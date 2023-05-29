import click
import cloup

from omnia.connection import get_mec
from omnia.ids.models import DataIdentifier

help_doc = """
Show the details of a DataIdentifier document, if it has already been saved.
"""


@cloup.command("show", no_args_is_help=True, help=help_doc)
@cloup.option("-l", "--label", help="Label used for the data identifier")
@click.pass_obj
def show(cm, label):
    mec = get_mec(cm.get_mdbc_db, cm.get_mdbc_uri)
    try:
        with mec:
            did = DataIdentifier.objects(unique_key=label).as_pymongo()[0]
            desc = did["description"] if "description" in did.keys() else None
            url = did["url"] if "url" in did.keys() else None
            _references = did["references"] if "references" in did.keys() else None
            articles = []
            if _references and len(_references) > 0:
                for a in _references:
                    article = DataIdentifier.objects().with_id(a)
                    articles.append({"title": article["title"], "url": article["url"], "uid": article["ext_uid"]})

            print("{}\n  description: {}\n  url: {}\n  articles: {}".format(label, desc, url, articles))
    except IndexError:
        print("Not found - This label has not been registered yet")

import click
import cloup

from omnia.connection import get_mec
from omnia.ids.models import DataIdentifier

help_doc = """
Show the details of a DataIdentifier document.
"""


@cloup.command("show", no_args_is_help=True, help=help_doc)
@cloup.option_group(
    "Search options",
    cloup.option("-l", "--label", help="Data identifier label, e.g.: gwas_1, article_1 ..."),
    cloup.option("-t", "--title", help="Data identifier title"),
    constraint=cloup.constraints.mutually_exclusive,
)
@cloup.option("-f", "--format", help="Output format", type=click.Choice(["csv", "box"]), default="box")
@click.pass_obj
def show(cm, format, label, title):
    mec = get_mec(cm.get_mdbc_db, cm.get_mdbc_uri)
    try:
        with mec:
            if label:
                result = DataIdentifier.objects(unique_key=label).as_pymongo()[0]
            else:
                result = DataIdentifier.objects(title__istartswith=title).as_pymongo()[0]
            unique_key = result["unique_key"]
            datatype = result["datatype"]
            _references = result["references"] if "references" in result.keys() else None
            articles = None
            if _references and len(_references) > 0:
                articles = []
                for a in _references:
                    article = DataIdentifier.objects().with_id(a)
                    articles.append({"title": article["title"], "url": article["url"], "uid": article["ext_uid"]})
            detail = {
                "desc": result["description"] if "description" in result.keys() else None,
                "url": result["url"] if "url" in result.keys() else None,
                "articles": articles,
                "uid": result["ext_uid"] if "ext_uid" in result.keys() else None,
                "title": result["title"] if "title" in result.keys() else None,
            }
            if datatype == "gwas":
                to_extract = ("desc", "url", "articles")
            else:
                to_extract = ("title", "url")
            if format == "box":
                print(f"{unique_key}")
                for k, v in detail.items():
                    if k in to_extract and v is not None:
                        print("  {}: {}".format(k, v))
            else:
                array = [unique_key]
                for k, v in detail.items():
                    if k in to_extract and v is not None:
                        array.append(v)
                print(*array, sep=",")
    except IndexError:
        print("Not found - A document with this label/title has not been recorded yet")

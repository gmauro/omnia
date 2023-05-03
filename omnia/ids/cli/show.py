from omnia.connection import get_mec
from omnia.ids.models import DataIdentifier, Reference

help_doc = """
Show the details of the DataIdentifier document, if it has already been saved.
"""


def make_parser(parser):
    parser.add_argument(
        "-l",
        "--label",
        type=str,
        metavar="LABEL",
        help="Label used for the data identifier",
    )


def implementation(logger, args):
    mec = get_mec(db=args.db, uri=args.uri)
    label = args.label
    label_args = label.split("_")
    if len(label_args) == 2 and len(label_args[1]) > 0:
        lb = label.split("_")[0]
        cn = label.split("_")[1]
        try:
            with mec:
                did = DataIdentifier.objects(label=lb, counter=cn).as_pymongo()[0]
                desc = did["description"] if "description" in did.keys() else None
                url = did["url"] if "url" in did.keys() else None
                _references = did["references"] if "references" in did.keys() else None
                articles = []
                if _references and len(_references) > 0:
                    for a in _references:
                        article = Reference.objects().with_id(a)
                        articles.append({"title": article["title"], "url": article["url"], "uid": article["uid"]})

                print("{}\n  description: {}\n  url: {}\n  articles: {}".format(label, desc, url, articles))
        except IndexError:
            print("Not found - This label has not been registered yet")
    else:
        print("Valid labels take this form: name_number ")


def do_register(registration_list):
    registration_list.append(("show", help_doc, make_parser, implementation))

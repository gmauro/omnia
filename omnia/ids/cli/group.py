import cloup

from omnia.ids.cli.add_article import add_article
from omnia.ids.cli.add_dataidentifier import create
from omnia.ids.cli.show import show


@cloup.group(
    invoke_without_command=True,
    no_args_is_help=True,
    help="Manage data identifiers.",
)
@cloup.pass_context
def did(ctx):
    pass


did.add_command(show)
did.add_command(create)
did.add_command(add_article)

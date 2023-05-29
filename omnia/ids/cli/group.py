import cloup

from omnia.ids.cli.add_article import add_article
from omnia.ids.cli.add_dataidentifier import add_trait
from omnia.ids.cli.show import show
from omnia.ids.cli.update_dataidentifier import update


@cloup.group(
    invoke_without_command=True,
    no_args_is_help=True,
    help="Manage data identifiers.",
)
@cloup.pass_context
def did(ctx):
    pass


did.add_command(show)
did.add_command(add_trait)
did.add_command(add_article)
did.add_command(update)

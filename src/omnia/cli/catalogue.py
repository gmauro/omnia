"""Catalogue lifecycle commands.

The grouped commands are the preferred public interface.  They delegate to
the established top-level commands so their database behaviour remains
identical while the CLI becomes clearer and less filesystem-like.
"""

import cloup

from omnia.cli.list import list_metadata
from omnia.cli.mkdir import add_collection
from omnia.cli.mv import edit_collection
from omnia.cli.rmdir import delete_collection


@cloup.group("catalogue", no_args_is_help=True, help="Create and manage Omnia catalogues.")
def catalogue() -> None:
    """Create and manage Omnia catalogues."""


@cloup.command("create", help="Create a catalogue in the database.")
@cloup.argument("name", help="Catalogue name")
@cloup.option("--description", help="Catalogue description")
@cloup.option("--keywords", help="Catalogue keyword; repeat the option for multiple keywords.", multiple=True)
def catalogue_create(name: str, description: str | None, keywords: tuple[str, ...]) -> None:
    """Create CATALOGUE."""
    add_collection.callback(name, description, list(keywords))


@cloup.command("list", help="List catalogues.")
def catalogue_list() -> None:
    """List catalogues in the database."""
    list_metadata.callback(None, False, False)


@cloup.command("describe", help="Show catalogue metadata and registered datasets.")
@cloup.argument("name", help="Catalogue name")
@cloup.option("-l", "--full-path", is_flag=True, help="Show registered dataset paths.")
def catalogue_describe(name: str, full_path: bool) -> None:
    """Describe CATALOGUE."""
    list_metadata.callback(name, full_path, False)


@cloup.command("verify", help="Verify checksums for datasets registered in a catalogue.")
@cloup.argument("name", help="Catalogue name")
def catalogue_verify(name: str) -> None:
    """Verify checksums for CATALOGUE."""
    list_metadata.callback(name, False, True)


@cloup.command("update", help="Update catalogue metadata.")
@cloup.argument("name", help="Catalogue name")
@cloup.argument("new-name", required=False, help="New catalogue name")
@cloup.option("-d", "--description", help="New catalogue description")
@cloup.option("--keywords", help="New catalogue keyword; repeat the option for multiple keywords.", multiple=True)
@cloup.option("--notes", help="New catalogue notes as JSON")
def catalogue_update(
    name: str, new_name: str | None, description: str | None, keywords: tuple[str, ...], notes: str | None
) -> None:
    """Update CATALOGUE."""
    edit_collection.callback(name, new_name, description, list(keywords), notes)


@cloup.command("delete", help="Delete a catalogue from the database.")
@cloup.argument("name", help="Catalogue name")
@cloup.option("-f", "--force", is_flag=True, help="Deregister its datasets before deleting the catalogue.")
def catalogue_delete(name: str, force: bool) -> None:
    """Delete CATALOGUE."""
    delete_collection.callback(name, force)


catalogue.add_command(catalogue_create)
catalogue.add_command(catalogue_list)
catalogue.add_command(catalogue_describe)
catalogue.add_command(catalogue_verify)
catalogue.add_command(catalogue_update)
catalogue.add_command(catalogue_delete)

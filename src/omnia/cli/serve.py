import click
import cloup

from omnia.mongo.mongo_manager import embedded_mongo, get_mongo_uri


@cloup.command("serve", no_args_is_help=False, help="Serve the application locally.")
@click.pass_context
def serve(ctx):
    with embedded_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)
        print(f"Serving embedded MongoDB at {mongo_uri}...")
        while True:
            pass

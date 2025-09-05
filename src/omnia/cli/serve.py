import click
import cloup
import uvicorn

from omnia.cli.fast_app import create_app
from omnia.mongo.mongo_manager import embedded_mongo, get_mongo_deployment, get_mongo_uri


class UvicornServer:
    def __init__(self, app, host="0.0.0.0", port=8000):
        self.app = app
        self.host = host
        self.port = port
        self.server = None

    def __enter__(self):
        self.server = uvicorn.Server(config=uvicorn.Config(self.app, host=self.host, port=self.port, log_level="info"))
        return self.server

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.server:
            self.server.should_exit = True
            self.server = None


@cloup.command("serve", no_args_is_help=False, help="Serve the application locally.")
@click.pass_context
def serve(ctx):
    with embedded_mongo(ctx):
        mongo_uri = get_mongo_uri(ctx)
        if get_mongo_deployment(ctx) == "embedded":
            print(f"Serving embedded MongoDB at {mongo_uri}...")
        app = create_app(mongo_uri, "omnia")
        with UvicornServer(app) as server:
            server.run()

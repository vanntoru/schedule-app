from __future__ import annotations

import code
import click

from schedule_app import create_app

@click.group(help="Schedule App management commands")
def cli() -> None:
    pass


@cli.command()
def shell() -> None:
    """Start an interactive Python shell."""
    ns = {"create_app": create_app}
    click.echo("Starting interactive shell...")
    code.interact(local=ns)


if __name__ == "__main__":
    cli()

from __future__ import annotations

import code
import click

from schedule_app import create_app

@click.group(help="Schedule App management commands")
def cli() -> None:
    """Management command group."""
    pass


def shell() -> None:
    """Start an interactive Python shell."""
    ns = {"create_app": create_app}
    click.echo("Starting interactive shell...")
    code.interact(local=ns)


@cli.command(name="shell")
def shell_cli() -> None:
    """Expose ``shell`` as a CLI command."""
    shell()


if __name__ == "__main__":
    cli()

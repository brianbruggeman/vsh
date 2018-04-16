from .click import api as click


def echo(message, verbose=None):
    if verbose or (verbose is None):
        click.echo(message)


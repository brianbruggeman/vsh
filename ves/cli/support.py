import sys

from .click import api as click


def echo(message, verbose=None):
    if verbose or (verbose is None):
        click.echo(message)


def prompt(prompt, valid_responses=None, default=None):
    """Interactive prompt

    Notes: This will only accept a single character from user input

    Args:
        prompt (str): Prompt to display
        valid_responses (list|tuple, optional): Valid keys [default: n, y]
        default (str, optional): Default argument [default: first accepted_args]
    """
    keys = valid_responses or ['n', 'y']
    default = default or keys.pop(0)
    prompt = f'{prompt} [{click.style(default, fg="blue")}{"".join(keys)}] '
    click.echo(prompt, nl=False)
    response = click.getchar()
    if response == '\r':
        response = default
    print(f'Default: {default}')
    print(f'Keys: {keys}')
    print(f'Response: {response}')
    if response not in keys + [default]:
        click.echo(response)
        sys.exit(0)
    click.echo()
    return response

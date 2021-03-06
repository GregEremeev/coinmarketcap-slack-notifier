import sys
import logging

import click

from coinmarketcap_slack_notifier import settings
from coinmarketcap_slack_notifier.core import AppRunner, Notifier, CoinManager


@click.group()
def commands_group():
    pass


@click.command()
def run_notifier():
    """Send notification about currency changes to the slack channel"""
    logging.config.dictConfig(settings.LOGGING)
    AppRunner(notifier=Notifier(), coin_manager=CoinManager()).run()


commands_group.add_command(run_notifier)


if __name__ == '__main__':
    sys.exit(commands_group())

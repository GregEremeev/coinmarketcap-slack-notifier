import json
from decimal import Decimal
from abc import ABCMeta, abstractmethod

from coinmarketcap_slack_notifier import settings


class ValueWasNotChanged(ValueError):
    pass


class CoinDoesNotExist(Exception):
    pass


def calculate_percent_changes(old_value, new_value):
    return (abs(new_value - old_value) / old_value * 100).quantize(settings.QUANTIZE_PERCENT_AND_PRICE)


def provide_sequence(obj):
    if isinstance(obj, (tuple, list)):
        return obj
    else:
        return (obj,)


def json_dumps(data):
    def default(obj):
        if isinstance(obj, Decimal):
            return str(obj)
    return json.dumps(data, default=default)


class BaseTriggerCondition(object):

    __metaclass__ = ABCMeta

    def __init__(self, value):
        self.value = value

    def _has_percent_changes_triggered(self, old_value, new_value):
        if calculate_percent_changes(old_value, new_value) >= self.value:
            return True
        else:
            return False

    @abstractmethod
    def has_condition_triggered(self, stored_coin, changed_coin):
        pass


class PercentUSDTriggerCondition(BaseTriggerCondition):

    def has_condition_triggered(self, stored_coin, changed_coin):
        return self._has_percent_changes_triggered(stored_coin.price_usd, changed_coin.price_usd)


class TotalSupplyTriggerCondition(BaseTriggerCondition):

    def has_condition_triggered(self, stored_coin, changed_coin):
        return self._has_percent_changes_triggered(stored_coin.total_supply, changed_coin.total_supply)

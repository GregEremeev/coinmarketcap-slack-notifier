import json
from collections import namedtuple

from decimal import Decimal

ObservableCoin = namedtuple('ObservableCoin', 'id icon_url percent')
StoredCoin = namedtuple('StoredCoin', 'id price_usd price_btc percent')
ChangedCoin = namedtuple('ChangedCoin', 'id price_usd price_btc')


class CoinDoesNotExist(Exception):
    pass


def json_dumps(data):
    def default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
    return json.dumps(data, default=default)

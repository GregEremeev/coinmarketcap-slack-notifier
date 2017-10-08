from collections import namedtuple


ObservableCoin = namedtuple('ObservableCoin', 'id icon_url percent')
StoredCoin = namedtuple('StoredCoin', 'id price_usd price_btc percent')


class CoinDoesNotExist(Exception):
    pass

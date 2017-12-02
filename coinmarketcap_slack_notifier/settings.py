import os
from decimal import Decimal


BASE_API_URL = 'https://api.coinmarketcap.com'
API_VERSION = '/v1'
TICKER_API_URL = '{}{}/ticker/'.format(BASE_API_URL, API_VERSION)


STORED_COINS_FILE_PATH = NotImplemented
OBSERVABLE_COINS = [
    {
        'id': 'bitcoin',
        'icon_url': 'https://pngimg.com/uploads/bitcoin/bitcoin_PNG6.png',
        'trigger_conditions': [{'percent_price_usd': 0.1, 'percent_total_supply': 0.1}, {'percent_price_usd': 0.1}],
        'slack_channel': 'general',
    },
    {
        'id': 'ethereum',
        'icon_url': 'https://cdn3.iconfinder.com/data/icons/inficons-set-2/512/648849-star-ratings-512.png',
        'trigger_conditions': [{'percent_coin_price_usd': 0.1}]
    },
]


CHANNEL_NAME = NotImplemented
SLACK_WEBHOOK_URL = NotImplemented
DISCORD_WEBHOOK_URL = NotImplemented
SENDER_USER_NAME = 'COINMARKETCAP_BOT'
ICON_EMOJI = ':robot_face:'


QUANTIZE_PERCENT_AND_PRICE = Decimal('0.00001')


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)-8s %(name)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'coinmarketcap_slack_notifier': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
         },
    }
}


CUSTOM_SETTINGS_PATH = os.getenv('NOTIFIER_SETTINGS', '/etc/notifier_settings.py')
exec(open(CUSTOM_SETTINGS_PATH).read())

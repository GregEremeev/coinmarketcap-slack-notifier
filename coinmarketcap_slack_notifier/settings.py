import os


BASE_API_URL = 'https://api.coinmarketcap.com'
API_VERSION = '/v1'
TICKER_API_URL = '{}{}/ticker/'.format(BASE_API_URL, API_VERSION)


STORED_COINS_FILE_PATH = NotImplemented
OBSERVABLE_COINS = [
    {'id': 'bitcoin',
     'icon_url': 'https://cdn3.iconfinder.com/data/icons/inficons-set-2/512/648849-star-ratings-512.png',
     'percent': 1},
    {'id': 'ethereum',
     'icon_url': 'https://cdn3.iconfinder.com/data/icons/inficons-set-2/512/648849-star-ratings-512.png',
     'percent': 2}
]


SLACK_CHANNEL = NotImplemented
SLACK_WEBHOOK_URL = NotImplemented
DISCORD_WEBHOOK_URL = NotImplemented
SENDER_USER_NAME = 'COINMARKETCAP_BOT'
ICON_EMOJI = ':robot_face:'


CUSTOM_SETTINGS_PATH = os.getenv('NOTIFIER_SETTINGS', '/etc/notifier_settings.py')
exec(open(CUSTOM_SETTINGS_PATH).read())

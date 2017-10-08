import json
import os
from decimal import Decimal

import requests

from coinmarketcap_slack_notifier import settings
from coinmarketcap_slack_notifier.utils import StoredCoin, ObservableCoin, CoinDoesNotExist


class CoinManager(object):

    def __init__(self):
        self.stored_coins = self._get_stored_coins()
        self.stored_coin_ids = [coin.id for coin in self.stored_coins]
        self.observable_coins = self._get_observable_coins()
        self.observable_coin_ids = [coin.id for coin in self.observable_coins]

    @staticmethod
    def _get_stored_coins():
        stored_coins = []
        if os.path.isfile(settings.STORED_COINS_FILE_PATH):
            with open(settings.STORED_COINS_FILE_PATH) as fin:
                for coin in fin:
                    stored_coins.append(StoredCoin(**json.loads(coin)))
        return stored_coins

    @staticmethod
    def _get_observable_coins():
        observable_coins = []
        for observable_coin_kwargs in settings.OBSERVABLE_COINS:
            observable_coins.append(ObservableCoin(**observable_coin_kwargs))
        return observable_coins

    def _has_currency_changed(self, currency):
        coin_id = currency['id']
        if coin_id in self.stored_coin_ids and coin_id in self.observable_coin_ids:
            stored_coin = self.get_stored_coin(coin_id)
            observable_coin = self.get_observable_coin(coin_id)
            if stored_coin.percent == observable_coin.percent:
                new_price_usd = Decimal(currency['price_usd'])
                old_price_usd = Decimal(str(stored_coin.price_usd))
                percent_changes = abs(new_price_usd - old_price_usd) / old_price_usd * 100
                if percent_changes >= Decimal(str(stored_coin.percent)):
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False

    def _get_coin(self, coin_id, coins):
        try:
            coin = filter(lambda x: x.id==coin_id, coins)[0]
        except IndexError:
            raise CoinDoesNotExist('Coin with id {} does not exist'.format(coin_id))
        else:
            return coin

    def get_stored_coin(self, coin_id):
        return self._get_coin(coin_id, self.stored_coins)

    def get_observable_coin(self, coin_id):
        return self._get_coin(coin_id, self.observable_coins)

    def get_changed_currency(self, current_currencies):
        changed_currency = []
        for current_currency in current_currencies:
            if self._has_currency_changed(current_currency):
                changed_currency.append(current_currency)

        return changed_currency

    def save_observable_currencies(self, currencies):
        with open(settings.STORED_COINS_FILE_PATH, 'w') as fout:
            for currency in currencies:
                currency_id = currency['id']
                if currency_id in self.observable_coin_ids:
                    observable_coin = self.get_observable_coin(currency['id'])
                    if self._has_currency_changed(currency) or currency_id not in self.stored_coin_ids:
                        currency_price_usd = float(currency['price_usd'])
                        currency_price_btc = float(currency['price_btc'])
                        currency_percent = float(observable_coin.percent)

                    else:
                        stored_coin = self.get_stored_coin(currency_id)
                        if stored_coin.percent == observable_coin.percent:
                            currency_price_usd = stored_coin.price_usd
                            currency_price_btc = stored_coin.price_btc
                            currency_percent = stored_coin.percent
                        else:
                            currency_price_usd = float(currency['price_usd'])
                            currency_price_btc = float(currency['price_btc'])
                            currency_percent = observable_coin.percent

                    fout.write(json.dumps({
                        'id': currency_id, 'price_usd': currency_price_usd, 'price_btc': currency_price_btc,
                        'percent': currency_percent}) + '\n')


class Notifier(object):

    ATTACHMENT_TITLE_TEMPLATE = '{coin_id} was changed on {percent} or more percent!\n'
    ATTACHMENT_TEXT_TEMPLATE = ('New price is *${new_price_usd}*, *btc {new_price_btc}*\n'
                                'Old price is *${old_price_usd}*, *btc {old_price_btc}*')

    def _get_attachment(self, observable_coin, stored_coin, new_price_usd, new_price_btc):
        title = self.ATTACHMENT_TITLE_TEMPLATE.format(
            coin_id=observable_coin.id.capitalize(), percent=observable_coin.percent)
        text = self.ATTACHMENT_TEXT_TEMPLATE.format(
            new_price_usd=new_price_usd, new_price_btc=new_price_btc,
            old_price_btc=stored_coin.price_btc, old_price_usd=stored_coin.price_usd)
        attachment = {
            'pretext': '*{coin_id}*'.format(coin_id=observable_coin.id.capitalize()),
            'title': title,
            'text': text,
            'thumb_url': observable_coin.icon_url,
            'title_link': 'https://coinmarketcap.com/currencies/{coin_id}/'.format(coin_id=observable_coin.id),
            'color': '#7CD197',
            'mrkdwn_in': ('pretext', 'text')
        }
        return attachment

    def _get_attachments(self, currency_data):
        attachments = []
        for observable_coin, stored_coin, changed_currency in currency_data:
            attachment = self._get_attachment(
                observable_coin, stored_coin, changed_currency['price_usd'], changed_currency['price_btc'])
            attachments.append(attachment)
        return attachments

    def _get_request_data(self, attachments):
        request_data = {
            'channel': '#' + settings.SLACK_CHANNEL,
            'username': settings.SENDER_USER_NAME,
            'attachments': attachments,
            'icon_emoji': settings.ICON_EMOJI,
        }
        return request_data

    def send_notification(self, currency_data):
        attachments = self._get_attachments(currency_data)
        requests.post(settings.SLACK_WEBHOOK_URL, json=self._get_request_data(attachments))


class AppRunner(object):

    def __init__(self, notifier, coin_manager):
        self.notifier = notifier
        self.coin_manager = coin_manager

    def get_currency_data(self, changed_currencies):
        currency_data = []
        for changed_currency in changed_currencies:
            changed_currency_id = changed_currency['id']
            observable_coin = self.coin_manager.get_observable_coin(changed_currency_id)
            stored_coin = self.coin_manager.get_stored_coin(changed_currency_id)
            currency_data.append((observable_coin, stored_coin, changed_currency))
        return currency_data

    def run(self):
        current_currencies = requests.get(settings.TICKER_API_URL).json()
        changed_currencies = self.coin_manager.get_changed_currency(current_currencies)
        if changed_currencies:
            currency_data = self.get_currency_data(changed_currencies)
            self.notifier.send_notification(currency_data)
        self.coin_manager.save_observable_currencies(current_currencies)

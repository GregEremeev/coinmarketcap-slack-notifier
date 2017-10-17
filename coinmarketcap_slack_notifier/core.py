import os
import json
from decimal import Decimal

import requests

from coinmarketcap_slack_notifier import settings
from coinmarketcap_slack_notifier.utils import StoredCoin, ObservableCoin, CoinDoesNotExist, ChangedCoin, json_dumps


class CoinManager(object):

    REQUIRED_COIN_FIELDS = ('id', 'price_usd', 'price_btc', 'percent')

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
                    data = json.loads(coin)
                    stored_coin = StoredCoin(id=data['id'], price_usd=Decimal(str(data['price_usd'])),
                                             price_btc=Decimal(str(data['price_btc'])),
                                             percent=Decimal(str(data['percent'])))
                    stored_coins.append(stored_coin)
        return stored_coins

    @staticmethod
    def _get_observable_coins():
        observable_coins = []
        for observable_coin_kwargs in settings.OBSERVABLE_COINS:
            observable_coin = ObservableCoin(
                id=observable_coin_kwargs['id'], icon_url=observable_coin_kwargs['icon_url'],
                percent=Decimal(str(observable_coin_kwargs['percent'])))
            observable_coins.append(observable_coin)
        return observable_coins

    def _has_currency_changed(self, changed_coin):
        coin_id = changed_coin.id
        if coin_id in self.stored_coin_ids and coin_id in self.observable_coin_ids:
            stored_coin = self.get_stored_coin(coin_id)
            observable_coin = self.get_observable_coin(coin_id)
            if stored_coin.percent == observable_coin.percent:
                new_price_usd = changed_coin.price_usd
                old_price_usd = stored_coin.price_usd
                if self.calculate_percent_changes(old_price_usd, new_price_usd) >= stored_coin.percent:
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

    def get_validated_currencies(self, current_currencies):
        validated_currencies = []
        for currency in current_currencies:
            if all(currency[key] is not None for key in self.REQUIRED_COIN_FIELDS):
                validated_currencies.append(validated_currencies)
        return validated_currencies

    def calculate_percent_changes(self, old_price_usd, new_price_usd):
        return (abs(new_price_usd - old_price_usd) / old_price_usd * 100).quantize(Decimal('0.1'))

    def get_stored_coin(self, coin_id):
        return self._get_coin(coin_id, self.stored_coins)

    def get_observable_coin(self, coin_id):
        return self._get_coin(coin_id, self.observable_coins)

    def get_changed_coins(self, current_currencies):
        changed_coins = []
        for current_currency in current_currencies:
            changed_coin = ChangedCoin(
                id=current_currency['id'], price_usd=Decimal(current_currency['price_usd']),
                price_btc=Decimal(current_currency['price_btc']))

            if self._has_currency_changed(changed_coin):
                changed_coins.append(changed_coin)

        return changed_coins

    def save_observable_currencies(self, currencies):
        with open(settings.STORED_COINS_FILE_PATH, 'w') as fout:
            for currency in currencies:
                potential_stored_coin = StoredCoin(
                    id=currency['id'], price_usd=Decimal(currency['price_usd']),
                    price_btc=Decimal(currency['price_btc']), percent=None)

                currency_id = potential_stored_coin.id
                if currency_id in self.observable_coin_ids:
                    observable_coin = self.get_observable_coin(currency['id'])
                    if self._has_currency_changed(potential_stored_coin) or currency_id not in self.stored_coin_ids:
                        currency_price_usd = potential_stored_coin.price_usd
                        currency_price_btc = potential_stored_coin.price_btc
                        currency_percent = observable_coin.percent

                    else:
                        stored_coin = self.get_stored_coin(currency_id)
                        if stored_coin.percent == observable_coin.percent:
                            currency_price_usd = stored_coin.price_usd
                            currency_price_btc = stored_coin.price_btc
                            currency_percent = stored_coin.percent
                        else:
                            currency_price_usd = potential_stored_coin.price_usd
                            currency_price_btc = potential_stored_coin.price_btc
                            currency_percent = observable_coin.percent

                    fout.write(json_dumps({
                        'id': currency_id, 'price_usd': currency_price_usd, 'price_btc': currency_price_btc,
                        'percent': currency_percent}) + '\n')


class Notifier(object):

    ATTACHMENT_TITLE_TEMPLATE = '{coin_id} {action} {percent}%'
    ATTACHMENT_TEXT_TEMPLATE = '_current price_ {price_btc}BTC, ${price_usd}'

    def _get_action(self, old_price_usd, new_price_usd):
        if old_price_usd > new_price_usd:
            return 'has fallen'
        elif old_price_usd < new_price_usd:
            return 'has risen'
        else:
            raise ValueError('Price was not changed')

    def _get_attachment(self, observable_coin, action, new_price_usd, new_price_btc, percent):
        title = self.ATTACHMENT_TITLE_TEMPLATE.format(
            coin_id=observable_coin.id.capitalize(), action=action, percent=percent)

        attachment = {
            'pretext': '*{coin_id}*'.format(coin_id=observable_coin.id.capitalize()),
            'title': title,
            'text': self.ATTACHMENT_TEXT_TEMPLATE.format(price_btc=new_price_btc, price_usd=new_price_usd),
            'thumb_url': observable_coin.icon_url,
            'title_link': 'https://coinmarketcap.com/currencies/{coin_id}/'.format(coin_id=observable_coin.id),
            'color': '#7CD197',
            'mrkdwn_in': ('pretext', 'text')
        }
        return attachment

    def _get_attachments(self, currency_data):
        attachments = []
        for observable_coin, stored_coin, changed_coin, percent in currency_data:
            action = self._get_action(stored_coin.price_usd, changed_coin.price_usd)
            attachment = self._get_attachment(
                observable_coin, action, changed_coin.price_usd, changed_coin.price_btc, percent)
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
        request_data = self._get_request_data(attachments)
        for webhook_url in (settings.SLACK_WEBHOOK_URL, settings.DISCORD_WEBHOOK_URL):
            if webhook_url is not NotImplemented:
                requests.post(webhook_url, json=request_data)


class AppRunner(object):

    def __init__(self, notifier, coin_manager):
        self.notifier = notifier
        self.coin_manager = coin_manager

    def get_currency_data(self, changed_coins):
        currency_data = []
        for changed_coin in changed_coins:
            changed_currency_id = changed_coin.id
            observable_coin = self.coin_manager.get_observable_coin(changed_currency_id)
            stored_coin = self.coin_manager.get_stored_coin(changed_currency_id)
            percent = self.coin_manager.calculate_percent_changes(stored_coin.price_usd, changed_coin.price_usd)
            currency_data.append((observable_coin, stored_coin, changed_coin, percent))
        return currency_data

    def run(self):
        current_currencies = requests.get(settings.TICKER_API_URL).json()
        changed_coins = self.coin_manager.get_changed_coins(current_currencies)
        if changed_coins:
            currency_data = self.get_currency_data(changed_coins)
            self.notifier.send_notification(currency_data)
        self.coin_manager.save_observable_currencies(current_currencies)

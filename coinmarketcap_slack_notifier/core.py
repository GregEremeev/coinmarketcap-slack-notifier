import os
import json
from decimal import Decimal

import requests

from coinmarketcap_slack_notifier import settings
from coinmarketcap_slack_notifier.utils import (StoredCoin, ObservableCoin, CoinDoesNotExist, ChangedCoin, json_dumps,
                                                AttachmentData, ValueWasNotChanged, provide_sequence)


class CoinManager(object):

    REQUIRED_COIN_FIELDS = ('id', 'price_usd', 'price_btc', 'total_supply', '24h_volume_usd')

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
                                             total_supply=Decimal(str(data['total_supply'])),
                                             percent=Decimal(str(data['percent'])))
                    stored_coins.append(stored_coin)
        return stored_coins

    @staticmethod
    def _get_observable_coins():
        observable_coins = []
        for observable_coin_kwargs in settings.OBSERVABLE_COINS:
            observable_coin = ObservableCoin(
                id=observable_coin_kwargs['id'], icon_url=observable_coin_kwargs['icon_url'],
                percent=Decimal(str(observable_coin_kwargs['percent'])),
                discord_webhook_url=observable_coin_kwargs.get('discord_webhook_url'),
                slack_channel=observable_coin_kwargs.get('slack_channel'))
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
                validated_currencies.append(currency)
        return validated_currencies

    def calculate_percent_changes(self, old_value, new_value):
        return (abs(new_value - old_value) / old_value * 100).quantize(settings.QUANTIZE_PERCENT_AND_PRICE)

    def get_stored_coin(self, coin_id):
        return self._get_coin(coin_id, self.stored_coins)

    def get_observable_coin(self, coin_id):
        return self._get_coin(coin_id, self.observable_coins)

    def get_changed_coins(self, current_currencies):
        changed_coins = []
        for current_currency in current_currencies:
            changed_coin = ChangedCoin(
                id=current_currency['id'], price_usd=Decimal(current_currency['price_usd']),
                price_btc=Decimal(current_currency['price_btc']),
                total_supply=Decimal(current_currency['total_supply']),
                daily_volume=float(current_currency['24h_volume_usd']))

            if self._has_currency_changed(changed_coin):
                changed_coins.append(changed_coin)

        return changed_coins

    def save_observable_currencies(self, currencies):
        with open(settings.STORED_COINS_FILE_PATH, 'w') as fout:
            for currency in currencies:
                potential_stored_coin = StoredCoin(
                    id=currency['id'], price_usd=Decimal(currency['price_usd']),
                    price_btc=Decimal(currency['price_btc']), total_supply=Decimal(currency['total_supply']),
                    percent=None)

                currency_id = potential_stored_coin.id
                if currency_id in self.observable_coin_ids:
                    observable_coin = self.get_observable_coin(currency['id'])
                    if self._has_currency_changed(potential_stored_coin) or currency_id not in self.stored_coin_ids:
                        currency_price_usd = potential_stored_coin.price_usd
                        currency_price_btc = potential_stored_coin.price_btc
                        currency_total_supply = potential_stored_coin.total_supply
                        currency_percent = observable_coin.percent

                    else:
                        stored_coin = self.get_stored_coin(currency_id)
                        if stored_coin.percent == observable_coin.percent:
                            currency_price_usd = stored_coin.price_usd
                            currency_price_btc = stored_coin.price_btc
                            currency_total_supply = stored_coin.total_supply
                            currency_percent = stored_coin.percent
                        else:
                            currency_price_usd = potential_stored_coin.price_usd
                            currency_price_btc = potential_stored_coin.price_btc
                            currency_total_supply = potential_stored_coin.total_supply
                            currency_percent = observable_coin.percent

                    fout.write(json_dumps({
                        'id': currency_id, 'price_usd': currency_price_usd, 'price_btc': currency_price_btc,
                        'total_supply': currency_total_supply, 'percent': currency_percent}) + '\n')


class Notifier(object):

    DEFAULT_WEBHOOK_URLS = (settings.SLACK_WEBHOOK_URL, settings.DISCORD_WEBHOOK_URL)
    ATTACHMENT_TITLE_TEMPLATE = '{coin_id} {action} {percent}%'
    ATTACHMENT_MAIN_TEXT_TEMPLATE = ('_current price_ {price_btc:,}BTC, ${price_usd:,}\n'
                                     '_24h volume_ is ${daily_volume:,}')
    ATTACHMENT_TOTAL_SUPPLY_TEXT_TEMPLATE = '\n_market cap_ {action} {coin_amount_change:,}, {btc_percent_change}%'

    def _get_attachment(self, attachment_data):
        title_link = 'https://coinmarketcap.com/currencies/{coin_id}/'.format(
            coin_id=attachment_data.observable_coin.id)

        title = self.ATTACHMENT_TITLE_TEMPLATE.format(
            coin_id=attachment_data.observable_coin.id.capitalize(),
            action=attachment_data.coin_price_action, percent=attachment_data.price_percent_change)
        text = self.ATTACHMENT_MAIN_TEXT_TEMPLATE.format(price_btc=attachment_data.new_price_btc,
                                                         price_usd=attachment_data.new_price_usd,
                                                         daily_volume=attachment_data.daily_volume)

        if attachment_data.coin_total_supply_action is not None:
            total_supply_text = self.ATTACHMENT_TOTAL_SUPPLY_TEXT_TEMPLATE.format(
                action=attachment_data.coin_total_supply_action, coin_amount_change=attachment_data.coin_amount_change,
                btc_percent_change=attachment_data.btc_percent_change)
            text += total_supply_text

        attachment = {
            'title': title,
            'text': text,
            'thumb_url': attachment_data.observable_coin.icon_url,
            'title_link': title_link,
            'color': '#7CD197',
            'mrkdwn_in': ('pretext', 'text')
        }
        return attachment

    def _get_request_data(self, attachments, channel):
        request_data = {
            'channel': '#' + channel,
            'username': settings.SENDER_USER_NAME,
            'attachments': attachments,
            'icon_emoji': settings.ICON_EMOJI,
        }
        return request_data

    def _send_notification(self, attachment_data, channel_name, webhook_urls):
        attachment = [self._get_attachment(attachment) for attachment in attachment_data]
        request_data = self._get_request_data(attachment, channel_name)
        for webhook_url in provide_sequence(webhook_urls):
            requests.post(webhook_url, json=request_data)

    def send_notification(self, attachments_data):
        all_attachments = []
        for attachment_data in attachments_data:
            slack_channel = attachment_data.observable_coin.slack_channel
            discord_webhook_url = attachment_data.observable_coin.discord_webhook_url
            if discord_webhook_url is not None:
                self._send_notification([attachment_data], '', discord_webhook_url)
            if slack_channel is not None:
                self._send_notification([attachment_data], slack_channel, settings.SLACK_WEBHOOK_URL)

            all_attachments.append(attachment_data)

        webhook_urls = [w for w in self.DEFAULT_WEBHOOK_URLS if w is not NotImplemented]
        self._send_notification(all_attachments, settings.CHANNEL_NAME, webhook_urls)

    def get_action(self, old_value, new_value):
        if old_value > new_value:
            return 'has fallen'
        elif old_value < new_value:
            return 'has risen'
        else:
            raise ValueWasNotChanged('Value was not changed')

class AppRunner(object):

    def __init__(self, notifier, coin_manager):
        self.notifier = notifier
        self.coin_manager = coin_manager

    def get_attachment_data(self, changed_coin):
        changed_currency_id = changed_coin.id
        stored_coin = self.coin_manager.get_stored_coin(changed_currency_id)
        try:
            coin_total_supply_action = self.notifier.get_action(stored_coin.total_supply, changed_coin.total_supply)
        except ValueWasNotChanged:
            coin_total_supply_action = None

        attachment_data = AttachmentData(
            observable_coin=self.coin_manager.get_observable_coin(changed_currency_id),
            coin_price_action=self.notifier.get_action(stored_coin.price_usd, changed_coin.price_usd),
            coin_total_supply_action=coin_total_supply_action,
            daily_volume=changed_coin.daily_volume,
            new_price_usd=changed_coin.price_usd,
            new_price_btc=changed_coin.price_btc,
            price_percent_change=self.coin_manager.calculate_percent_changes(
                stored_coin.price_usd, changed_coin.price_usd),
            coin_amount_change=(abs(stored_coin.total_supply - changed_coin.total_supply)
                                .quantize(settings.QUANTIZE_PERCENT_AND_PRICE)),
            btc_percent_change=self.coin_manager.calculate_percent_changes(
                stored_coin.total_supply, changed_coin.total_supply))

        return attachment_data

    def run(self):
        current_currencies = requests.get(settings.TICKER_API_URL).json()
        validated_currencies = self.coin_manager.get_validated_currencies(current_currencies)
        changed_coins = self.coin_manager.get_changed_coins(validated_currencies)
        if changed_coins:
            attachment_data = [self.get_attachment_data(changed_coin) for changed_coin in changed_coins]
            self.notifier.send_notification(attachment_data)
        self.coin_manager.save_observable_currencies(validated_currencies)

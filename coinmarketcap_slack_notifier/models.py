from decimal import Decimal
from collections import namedtuple


class BaseCoin(object):

    def __init__(self, id, trigger_conditions):
        self.id = id
        self.trigger_conditions = trigger_conditions

    @property
    def trigger_conditions(self):
        return self._trigger_conditions

    @trigger_conditions.setter
    def trigger_conditions(self, trigger_conditions):
        for trigger_subconditions in trigger_conditions:
            for subcondition_name, subcondition_value in trigger_subconditions.iteritems():
                trigger_subconditions[subcondition_name] = Decimal(str(subcondition_value))
        self._trigger_conditions = trigger_conditions


class ObservableCoin(BaseCoin):

    def __init__(self, id, trigger_conditions, icon_url, slack_channel, discord_webhook_url):
        self.icon_url = icon_url
        self.slack_channel = slack_channel
        self.discord_webhook_url = discord_webhook_url
        super(ObservableCoin, self).__init__(id, trigger_conditions)


class StoredCoin(BaseCoin):

    def __init__(self, id, trigger_conditions, price_usd, price_btc, total_supply):
        self.price_usd = Decimal(str(price_usd))
        self.price_btc = Decimal(str(price_btc))
        self.total_supply = Decimal(str(total_supply))
        super(StoredCoin, self).__init__(id, trigger_conditions)


ChangedCoin = namedtuple('ChangedCoin', 'id price_usd price_btc total_supply daily_volume')
AttachmentData = namedtuple('AttachmentData', 'observable_coin coin_price_action coin_total_supply_action '
                                              'new_price_usd new_price_btc daily_volume price_percent_change '
                                              'coin_amount_change btc_percent_change')
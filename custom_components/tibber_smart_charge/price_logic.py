"""Price logic."""

from copy import deepcopy
from datetime import timedelta
import logging

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


class PriceLogic:
    """Price logic for smart charging."""

    def __init__(self, price_dict):
        """Init."""
        # self._price_list = list(price_dict.items())
        self._price_list = [
            (dt_util.parse_datetime(ts), price) for ts, price in price_dict.items()
        ]
        self._price_list.sort(key=lambda a: a[0])

    def find_cheapest_hours(self, count, time_from=None, before_hour=None):
        """Find cheapest number of hours starting from time_from."""
        filtered_list = deepcopy(self._price_list)
        if time_from:
            filtered_list = list(filter(lambda ti: ti[0] >= time_from, filtered_list))
        if before_hour:
            max_time = time_from.replace(hour=before_hour)
            if time_from.hour >= before_hour:
                max_time = time_from + timedelta(days=1)

            filtered_list = list(filter(lambda ti: ti[0] < max_time, filtered_list))

        filtered_list.sort(key=lambda a: a[1])

        result = filtered_list[0:count]
        result.sort(key=lambda a: a[0])

        return result

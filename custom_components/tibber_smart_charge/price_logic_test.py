"""Test of price logic."""
import unittest

import price_logic

from homeassistant.util import dt as dt_util

prices = {
    "2023-01-02T00:00:00.000+01:00": 0.9143,
    "2023-01-02T01:00:00.000+01:00": 0.8275,
    "2023-01-02T02:00:00.000+01:00": 0.8441,
    "2023-01-02T03:00:00.000+01:00": 0.7232,
    "2023-01-02T04:00:00.000+01:00": 0.8054,
    "2023-01-02T05:00:00.000+01:00": 1.0925,
    "2023-01-02T06:00:00.000+01:00": 1.5349,
    "2023-01-02T07:00:00.000+01:00": 2.0301,
    "2023-01-02T08:00:00.000+01:00": 2.1384,
    "2023-01-02T09:00:00.000+01:00": 2.1532,
    "2023-01-02T10:00:00.000+01:00": 2.1332,
    "2023-01-02T11:00:00.000+01:00": 2.1018,
    "2023-01-02T12:00:00.000+01:00": 2.1161,
    "2023-01-02T13:00:00.000+01:00": 2.1075,
    "2023-01-02T14:00:00.000+01:00": 2.1692,
    "2023-01-02T15:00:00.000+01:00": 2.2685,
    "2023-01-02T16:00:00.000+01:00": 2.3734,
    "2023-01-02T17:00:00.000+01:00": 2.4722,
    "2023-01-02T18:00:00.000+01:00": 2.5381,
    "2023-01-02T19:00:00.000+01:00": 2.3952,
    "2023-01-02T20:00:00.000+01:00": 2.2359,
    "2023-01-02T21:00:00.000+01:00": 2.0785,
    "2023-01-02T22:00:00.000+01:00": 1.9395,
    "2023-01-02T23:00:00.000+01:00": 1.7503,
    "2023-01-03T00:00:00.000+01:00": 0.9143,
    "2023-01-03T01:00:00.000+01:00": 0.8275,
    "2023-01-03T02:00:00.000+01:00": 0.8441,
    "2023-01-03T03:00:00.000+01:00": 0.7232,
    "2023-01-03T04:00:00.000+01:00": 0.8054,
    "2023-01-03T05:00:00.000+01:00": 1.0925,
    "2023-01-03T06:00:00.000+01:00": 1.5349,
    "2023-01-03T07:00:00.000+01:00": 2.0301,
    "2023-01-03T08:00:00.000+01:00": 2.1384,
    "2023-01-03T09:00:00.000+01:00": 2.1532,
    "2023-01-03T10:00:00.000+01:00": 2.1332,
    "2023-01-03T11:00:00.000+01:00": 2.1018,
    "2023-01-03T12:00:00.000+01:00": 2.1161,
    "2023-01-03T13:00:00.000+01:00": 2.1075,
    "2023-01-03T14:00:00.000+01:00": 2.1692,
    "2023-01-03T15:00:00.000+01:00": 2.2685,
    "2023-01-03T16:00:00.000+01:00": 2.3734,
    "2023-01-03T17:00:00.000+01:00": 2.4722,
    "2023-01-03T18:00:00.000+01:00": 2.5381,
    "2023-01-03T19:00:00.000+01:00": 2.3952,
    "2023-01-03T20:00:00.000+01:00": 2.2359,
    "2023-01-03T21:00:00.000+01:00": 2.0785,
    "2023-01-03T22:00:00.000+01:00": 1.9395,
    "2023-01-03T23:00:00.000+01:00": 1.7503,
}


class MyTestCase(unittest.TestCase):
    """Test of price logic."""

    def test_find_cheapest_hour(self):
        """Test of price logic."""
        pl = price_logic.PriceLogic(prices)

        cheapest = pl.find_cheapest_hours(1)
        self.assertTimeAndPrice(cheapest[0], 0.7232, "2023-01-02T03:00:00.000+01:00")

        cheapest = pl.find_cheapest_hours(2)
        self.assertTimeAndPrice(cheapest[0], 0.7232, "2023-01-02T03:00:00.000+01:00")
        self.assertTimeAndPrice(cheapest[1], 0.7232, "2023-01-03T03:00:00.000+01:00")

        cheapest = pl.find_cheapest_hours(3)
        self.assertTimeAndPrice(cheapest[0], 0.7232, "2023-01-02T03:00:00.000+01:00")
        self.assertTimeAndPrice(cheapest[1], 0.8054, "2023-01-02T04:00:00.000+01:00")
        self.assertTimeAndPrice(cheapest[2], 0.7232, "2023-01-03T03:00:00.000+01:00")

    def assertTimeAndPrice(self, priceTuple, price, timestamp):
        self.assertEqual(dt_util.parse_datetime(timestamp), priceTuple[0])
        self.assertEqual(price, priceTuple[1])

    def test_find_cheapest_hour_with_start_time(self):
        """Test of price logic."""
        pl = price_logic.PriceLogic(prices)

        cheapest = pl.find_cheapest_hours(
            1, dt_util.parse_datetime("2023-01-02T04:00:00.000+01:00")
        )
        self.assertTimeAndPrice(cheapest[0], 0.7232, "2023-01-03T03:00:00.000+01:00")

        cheapest = pl.find_cheapest_hours(
            2, dt_util.parse_datetime("2023-01-02T04:00:00.000+01:00")
        )
        self.assertTimeAndPrice(cheapest[0], 0.8054, "2023-01-02T04:00:00.000+01:00")
        self.assertTimeAndPrice(cheapest[1], 0.7232, "2023-01-03T03:00:00.000+01:00")

        cheapest = pl.find_cheapest_hours(
            3, dt_util.parse_datetime("2023-01-02T04:00:00.000+01:00")
        )
        self.assertTimeAndPrice(cheapest[0], 0.8054, "2023-01-02T04:00:00.000+01:00")
        self.assertTimeAndPrice(cheapest[1], 0.7232, "2023-01-03T03:00:00.000+01:00")
        self.assertTimeAndPrice(cheapest[2], 0.8054, "2023-01-03T04:00:00.000+01:00")

    def test_find_cheapest_hour_with_start_and_end_time(self):
        """Test of price logic."""
        pl = price_logic.PriceLogic(prices)

        cheapest = pl.find_cheapest_hours(
            1, dt_util.parse_datetime("2023-01-02T00:00:00.000+01:00"), 7
        )
        self.assertTimeAndPrice(cheapest[0], 0.7232, "2023-01-02T03:00:00.000+01:00")

        cheapest = pl.find_cheapest_hours(
            1, dt_util.parse_datetime("2023-01-02T05:00:00.000+01:00"), 7
        )
        self.assertTimeAndPrice(cheapest[0], 1.0925, "2023-01-02T05:00:00.000+01:00")


if __name__ == "__main__":
    unittest.main()

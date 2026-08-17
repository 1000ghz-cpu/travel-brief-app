#!/usr/bin/env python3
"""Tests for travelbrief.py. Run with: python3 -m unittest test_travelbrief.py -v"""
import unittest
from unittest.mock import MagicMock, patch

from travelbrief import build_brief

GEOCODE_RESULT = {
    "results": [
        {
            "name": "Tokyo",
            "latitude": 35.6895,
            "longitude": 139.6917,
            "timezone": "Asia/Tokyo",
            "country": "Japan",
            "country_code": "JP",
        }
    ]
}
FORECAST_RESULT = {
    "current": {"temperature_2m": 27.9, "weather_code": 1, "wind_speed_10m": 6.0}
}
EXCHANGE_RESULT = {"amount": 1, "base": "USD", "rates": {"JPY": 159.01}}


def mock_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class BuildBriefTests(unittest.TestCase):
    @patch("travelbrief.requests.get")
    def test_known_city_includes_weather_and_exchange_rate(self, mock_get):
        mock_get.side_effect = [
            mock_response(GEOCODE_RESULT),
            mock_response(FORECAST_RESULT),
            mock_response(EXCHANGE_RESULT),
        ]

        brief = build_brief("Tokyo")

        self.assertIn("Tokyo, Japan", brief)
        self.assertIn("Mainly clear", brief)
        self.assertIn("27.9", brief)
        self.assertIn("159.01 JPY", brief)

    @patch("travelbrief.requests.get")
    def test_unknown_city_returns_none(self, mock_get):
        mock_get.return_value = mock_response({"results": []})

        self.assertIsNone(build_brief("Zzzznotacity"))

    @patch("travelbrief.requests.get")
    def test_usd_country_skips_exchange_rate_lookup(self, mock_get):
        geocode_usa = {
            "results": [
                {
                    "name": "New York",
                    "latitude": 40.71,
                    "longitude": -74.01,
                    "timezone": "America/New_York",
                    "country": "United States",
                    "country_code": "US",
                }
            ]
        }
        mock_get.side_effect = [mock_response(geocode_usa), mock_response(FORECAST_RESULT)]

        brief = build_brief("New York")

        self.assertIn("1 USD = 1.00 USD", brief)
        self.assertEqual(mock_get.call_count, 2)  # no exchange-rate call needed


if __name__ == "__main__":
    unittest.main()

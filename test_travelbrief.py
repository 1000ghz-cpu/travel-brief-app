#!/usr/bin/env python3
"""Tests for travelbrief.py. Run with: python3 -m unittest test_travelbrief.py -v"""
import time
import unittest
from unittest.mock import MagicMock, patch

import requests

import travelbrief
from travelbrief import build_brief

# haversine_km/estimate_fare are defined in app.py (which builds on travelbrief.py's
# geocoding/brief functions), not in travelbrief.py itself.
from app import FARE_PER_KM, MINIMUM_FARE, estimate_fare, haversine_km

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
    def setUp(self):
        # The weather/exchange/air-quality caches are module-level, so clear
        # them before each test to avoid one test's cached response leaking
        # into another.
        travelbrief._weather_cache.clear()
        travelbrief._exchange_cache.clear()
        travelbrief._air_quality_cache.clear()

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

    @patch("travelbrief.requests.get")
    def test_air_quality_error_degrades_gracefully(self, mock_get):
        mock_get.side_effect = [
            mock_response(GEOCODE_RESULT),
            mock_response(FORECAST_RESULT),
            mock_response(EXCHANGE_RESULT),
            requests.exceptions.HTTPError("401 Client Error: Unauthorized"),
        ]

        brief = build_brief("Tokyo", openweather_api_key="badkey")

        self.assertIn("Tokyo, Japan", brief)
        self.assertIn("Air quality: Unknown", brief)

    @patch("travelbrief.requests.get")
    def test_second_call_for_same_city_reuses_cached_weather_and_exchange_rate(self, mock_get):
        mock_get.side_effect = [
            mock_response(GEOCODE_RESULT),
            mock_response(FORECAST_RESULT),
            mock_response(EXCHANGE_RESULT),
            mock_response(GEOCODE_RESULT),  # geocoding isn't cached
        ]

        first = build_brief("Tokyo")
        second = build_brief("Tokyo")

        self.assertEqual(first, second)
        # Only 4 requests total: 2 geocode calls, but weather and exchange
        # rate are served from cache on the second call instead of 2 more.
        self.assertEqual(mock_get.call_count, 4)

    @patch("travelbrief.requests.get")
    def test_expired_cache_entry_triggers_new_request(self, mock_get):
        mock_get.side_effect = [
            mock_response(GEOCODE_RESULT),
            mock_response(FORECAST_RESULT),
            mock_response(EXCHANGE_RESULT),
            mock_response(GEOCODE_RESULT),
            mock_response(FORECAST_RESULT),
            mock_response(EXCHANGE_RESULT),
        ]

        build_brief("Tokyo")
        with patch("travelbrief.time.time", return_value=time.time() + travelbrief.CACHE_TTL_SECONDS + 1):
            build_brief("Tokyo")

        self.assertEqual(mock_get.call_count, 6)


class HaversineKmTests(unittest.TestCase):
    def test_new_york_to_london_matches_known_distance(self):
        # Real-world great-circle distance is ~5570 km.
        distance = haversine_km(40.7128, -74.0060, 51.5074, -0.1278)

        self.assertAlmostEqual(distance, 5570, delta=20)

    def test_paris_to_london_matches_known_distance(self):
        # Real-world great-circle distance is ~344 km.
        distance = haversine_km(48.8566, 2.3522, 51.5074, -0.1278)

        self.assertAlmostEqual(distance, 344, delta=10)

    def test_tokyo_to_sydney_matches_known_distance(self):
        # Real-world great-circle distance is ~7823 km.
        distance = haversine_km(35.6762, 139.6503, -33.8688, 151.2093)

        self.assertAlmostEqual(distance, 7823, delta=30)

    def test_identical_origin_and_destination_is_zero(self):
        distance = haversine_km(35.6895, 139.6917, 35.6895, 139.6917)

        self.assertEqual(distance, 0.0)

    def test_distance_is_symmetric(self):
        forward = haversine_km(40.7128, -74.0060, 51.5074, -0.1278)
        backward = haversine_km(51.5074, -0.1278, 40.7128, -74.0060)

        self.assertAlmostEqual(forward, backward, places=9)


class EstimateFareTests(unittest.TestCase):
    def test_zero_distance_returns_minimum_fare(self):
        self.assertEqual(estimate_fare(0), MINIMUM_FARE)

    def test_short_distance_below_minimum_returns_minimum_fare(self):
        # At FARE_PER_KM=0.12 and MINIMUM_FARE=40.0, distances under ~333 km
        # would otherwise price below the minimum fare.
        short_distance = 50.0

        self.assertEqual(estimate_fare(short_distance), MINIMUM_FARE)

    def test_long_distance_scales_linearly_with_distance(self):
        distance = 5570.2  # New York -> London

        fare = estimate_fare(distance)

        self.assertAlmostEqual(fare, distance * FARE_PER_KM, places=6)
        self.assertGreater(fare, MINIMUM_FARE)


if __name__ == "__main__":
    unittest.main()

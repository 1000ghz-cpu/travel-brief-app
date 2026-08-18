#!/usr/bin/env python3
"""Tests for app.py. Run with: python3 -m unittest test_app.py -v"""
import os
import unittest
from unittest.mock import patch

from app import app

HOME_PLACE = {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "country_code": "IN"}


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_patcher.start()
        os.environ.pop("OPENWEATHER_API_KEY", None)

    def tearDown(self):
        self.env_patcher.stop()

    def test_index_shows_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your name", response.data)
        self.assertIn(b"Home location", response.data)

    @patch("app.geocode_city")
    def test_index_post_stores_session_and_redirects(self, mock_geocode_city):
        mock_geocode_city.return_value = HOME_PLACE

        response = self.client.post(
            "/", data={"name": "Priya", "age": "29", "home_location": "Mumbai"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/explore", response.headers["Location"])
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["name"], "Priya")
            self.assertEqual(sess["age"], 29)
            self.assertEqual(sess["home_location"], "Mumbai")

    def test_index_post_rejects_missing_fields(self):
        response = self.client.post("/", data={"name": "", "age": "", "home_location": ""})

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Please fill in your name, age, and home location", response.data)

    @patch("app.geocode_city")
    def test_index_post_returns_404_for_unknown_home_location(self, mock_geocode_city):
        mock_geocode_city.return_value = None

        response = self.client.post(
            "/", data={"name": "Priya", "age": "29", "home_location": "Zzzznotacity"}
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Could not find a location", response.data)

    def test_explore_redirects_without_session(self):
        response = self.client.get("/explore")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.headers["Location"])

    @patch("app.geocode_city")
    def test_explore_shows_map_with_session(self, mock_geocode_city):
        mock_geocode_city.return_value = HOME_PLACE
        self.client.post("/", data={"name": "Priya", "age": "29", "home_location": "Mumbai"})

        response = self.client.get("/explore")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Hi Priya", response.data)
        self.assertIn(b"Tokyo", response.data)

    def test_city_data_requires_session(self):
        response = self.client.get("/city-data/Tokyo")

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"start from the homepage", response.data)

    @patch("app.geocode_city")
    def test_city_data_returns_404_for_unknown_city(self, mock_geocode_city):
        mock_geocode_city.return_value = HOME_PLACE
        self.client.post("/", data={"name": "Priya", "age": "29", "home_location": "Mumbai"})

        response = self.client.get("/city-data/Atlantis")

        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Unknown city", response.data)

    @patch("app.build_brief")
    @patch("app.geocode_city")
    def test_city_data_returns_brief_and_recommendation(self, mock_geocode_city, mock_build_brief):
        mock_geocode_city.return_value = HOME_PLACE
        mock_build_brief.return_value = "Travel Brief: Tokyo, Japan\n----\nWeather: Mainly clear"
        self.client.post("/", data={"name": "Priya", "age": "29", "home_location": "Mumbai"})

        response = self.client.get("/city-data/Tokyo")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["city"], "Tokyo")
        self.assertEqual(data["origin"], "Mumbai")
        self.assertEqual(data["age_bracket"], "26-40")
        self.assertIsNotNone(data["recommendation"])
        labels = [row["label"] for row in data["brief_rows"]]
        self.assertIn("Weather", labels)
        self.assertIn("Distance from home", labels)
        self.assertIn("Estimated fare — rough approximation, not live pricing", labels)


if __name__ == "__main__":
    unittest.main()

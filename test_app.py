#!/usr/bin/env python3
"""Tests for app.py. Run with: python3 -m unittest test_app.py -v"""
import os
import unittest
from unittest.mock import patch

from app import app


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
        self.assertIn(b"City name", response.data)
        self.assertIn(b"Age", response.data)

    @patch("app.build_brief")
    def test_brief_renders_result_for_known_city(self, mock_build_brief):
        mock_build_brief.return_value = "Travel Brief: Tokyo, Japan\nWeather: Mainly clear"

        response = self.client.post("/brief", data={"city": "Tokyo", "age": "29"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tokyo", response.data)
        self.assertIn(b"age 29", response.data)
        self.assertIn(b"Mainly clear", response.data)
        mock_build_brief.assert_called_once_with("Tokyo", None)

    @patch("app.build_brief")
    def test_brief_returns_404_for_unknown_city(self, mock_build_brief):
        mock_build_brief.return_value = None

        response = self.client.post("/brief", data={"city": "Zzzznotacity", "age": "29"})

        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Could not find a city", response.data)

    def test_brief_rejects_missing_fields(self):
        response = self.client.post("/brief", data={"city": "", "age": ""})

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Please enter a city name and a valid age", response.data)


if __name__ == "__main__":
    unittest.main()

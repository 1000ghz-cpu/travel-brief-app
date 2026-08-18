#!/usr/bin/env python3
"""Flask web app for travelbrief: a two-page trip explorer.

Page 1 ("/") collects the traveler's name, age, and home location and
stores them in the session. Page 2 ("/explore") shows an interactive
Leaflet.js map of 15 destination cities; clicking a marker fetches
"/city-data/<city>" for weather, currency, air quality, distance/fare
from the traveler's home location, and age-appropriate venue
recommendations, and renders them in a details panel without a page
reload.

Reuses the API logic from travelbrief.py. Air quality requires an
OpenWeatherMap API key in the OPENWEATHER_API_KEY environment variable
(get one at https://openweathermap.org/api).

Example usage:
    python3 app.py
    # then open http://127.0.0.1:5001 in a browser

    OPENWEATHER_API_KEY=your_key_here python3 app.py
"""
import json
import math
import os
import re
from urllib.parse import quote

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from travelbrief import COUNTRY_TO_CURRENCY, build_brief, geocode_city

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

EARTH_RADIUS_KM = 6371.0
FARE_PER_KM = 0.12
MINIMUM_FARE = 40.0

WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
# Wikipedia's API rejects requests.py's default User-Agent with a 403 — a descriptive
# one is required by their API etiquette policy.
WIKIPEDIA_HEADERS = {"User-Agent": "travelbrief-app/1.0 (educational project)"}

# Destination cities shown as map markers on the explore page.
CITIES = [
    {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503},
    {"name": "Bangkok", "lat": 13.7563, "lon": 100.5018},
    {"name": "Bali", "lat": -8.3405, "lon": 115.0920},
    {"name": "Dubai", "lat": 25.2048, "lon": 55.2708},
    {"name": "Singapore", "lat": 1.3521, "lon": 103.8198},
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"name": "London", "lat": 51.5074, "lon": -0.1278},
    {"name": "Rome", "lat": 41.9028, "lon": 12.4964},
    {"name": "Barcelona", "lat": 41.3851, "lon": 2.1734},
    {"name": "Amsterdam", "lat": 52.3676, "lon": 4.9041},
    {"name": "New York", "lat": 40.7128, "lon": -74.0060},
    {"name": "Cancun", "lat": 21.1619, "lon": -86.8515},
    {"name": "Rio de Janeiro", "lat": -22.9068, "lon": -43.1729},
    {"name": "Cape Town", "lat": -33.9249, "lon": 18.4241},
    {"name": "Sydney", "lat": -33.8688, "lon": 151.2093},
    {"name": "Istanbul", "lat": 41.0082, "lon": 28.9784},
]
CITY_LOOKUP = {city["name"].lower(): city for city in CITIES}

RECOMMENDATIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "travel_recommendations.json")
with open(RECOMMENDATIONS_PATH, encoding="utf-8") as f:
    TRAVEL_RECOMMENDATIONS = json.load(f)

# Age bracket label -> (min, max) inclusive; max of None means no upper bound.
AGE_BRACKETS = [
    ("18-25", 18, 25),
    ("26-40", 26, 40),
    ("41-60", 41, 60),
    ("60+", 61, None),
]

# Label (as produced by build_brief) -> icon shown next to it in the details panel.
BRIEF_ICONS = {
    "Location": "📍",
    "Weather": "🌤️",
    "Temperature": "🌡️",
    "Wind speed": "💨",
    "Exchange rate": "💱",
    "Air quality": "🌬️",
}
DEFAULT_BRIEF_ICON = "•"


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in kilometers."""
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = (math.radians(v) for v in (lat1, lon1, lat2, lon2))
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def estimate_fare(distance_km):
    """Rough distance-based fare estimate — not live pricing."""
    return max(MINIMUM_FARE, distance_km + FARE_PER_KM)


def get_age_bracket(age):
    """Return the bracket label containing `age`, or None."""
    for label, low, high in AGE_BRACKETS:
        if age >= low and (high is None or age <= high):
            return label
    return None


def fetch_wikipedia_summary(title, cache):
    """Look up a Wikipedia page summary for `title`, or None if unavailable.

    Results are memoized in `cache` (a dict the caller owns, typically scoped
    to one request) since the same venue or city name can otherwise be looked
    up more than once per request.
    """
    if title in cache:
        return cache[title]

    summary = None
    try:
        response = requests.get(
            WIKIPEDIA_SUMMARY_URL.format(quote(title, safe="")),
            headers=WIKIPEDIA_HEADERS,
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            summary = {
                "extract": data.get("extract"),
                "thumbnail": (data.get("thumbnail") or {}).get("source"),
            }
    except requests.RequestException:
        summary = None

    cache[title] = summary
    return summary


def first_sentences(text, count=2):
    """Return the first `count` sentences of `text`, or None if `text` is empty."""
    if not text:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:count]).strip()


def parse_brief(brief_text):
    """Split build_brief's "Title\\n----\\nLabel: value\\n..." text into a title and rows."""
    lines = brief_text.splitlines()
    title = lines[0]
    rows = []
    for line in lines[2:]:
        label, _, value = line.partition(": ")
        rows.append({"icon": BRIEF_ICONS.get(label, DEFAULT_BRIEF_ICON), "label": label, "value": value})
    return title, rows


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html", error=None)

    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()
    home_location = request.form.get("home_location", "").strip()

    if not name or not age.isdigit() or not home_location:
        return render_template("index.html", error="Please fill in your name, age, and home location."), 400

    try:
        home_place = geocode_city(home_location)
    except requests.RequestException as exc:
        return render_template("index.html", error=f"Network error while looking up '{home_location}': {exc}"), 502

    if home_place is None:
        return render_template("index.html", error=f"Could not find a location named '{home_location}'."), 404

    session["name"] = name
    session["age"] = int(age)
    session["home_location"] = home_location
    session["home_lat"] = home_place["latitude"]
    session["home_lon"] = home_place["longitude"]
    session["home_currency"] = COUNTRY_TO_CURRENCY.get(home_place.get("country_code", ""))

    return redirect(url_for("explore"))


@app.route("/explore")
def explore():
    if "home_location" not in session:
        return redirect(url_for("index"))

    return render_template(
        "explore.html",
        name=session["name"],
        age=session["age"],
        home_location=session["home_location"],
        cities=CITIES,
    )


@app.route("/city-data/<city>")
def city_data(city):
    if "home_location" not in session:
        return jsonify({"error": "Please start from the homepage."}), 400

    city_info = CITY_LOOKUP.get(city.strip().lower())
    if city_info is None:
        return jsonify({"error": f"Unknown city '{city}'."}), 404

    canonical_city = city_info["name"]
    openweather_api_key = os.environ.get("OPENWEATHER_API_KEY")
    home_currency = session.get("home_currency")

    try:
        brief_text = build_brief(canonical_city, openweather_api_key, base_currency=home_currency)
    except requests.RequestException as exc:
        return jsonify({"error": f"Network error while fetching travel brief: {exc}"}), 502

    if brief_text is None:
        return jsonify({"error": f"Could not find data for '{canonical_city}'."}), 404

    _, brief_rows = parse_brief(brief_text)

    distance_km = haversine_km(
        session["home_lat"], session["home_lon"], city_info["lat"], city_info["lon"]
    )
    brief_rows.append({"icon": "📏", "label": "Distance from home", "value": f"{distance_km:.0f} km"})
    brief_rows.append({
        "icon": "💵",
        "label": "Estimated fare — rough approximation, not live pricing",
        "value": f"${estimate_fare(distance_km):.2f}",
    })

    wiki_cache = {}
    city_summary = fetch_wikipedia_summary(canonical_city, wiki_cache)
    city_blurb = first_sentences(city_summary["extract"], 2) if city_summary else None

    age_bracket = get_age_bracket(session["age"])
    recommendation = TRAVEL_RECOMMENDATIONS.get(canonical_city, {}).get(age_bracket)
    if recommendation:
        venues = []
        for venue_name in recommendation["venues"]:
            venue_summary = fetch_wikipedia_summary(venue_name, wiki_cache)
            venues.append({
                "name": venue_name,
                "thumbnail": venue_summary["thumbnail"] if venue_summary else None,
            })
        recommendation = {"style": recommendation["style"], "venues": venues}

    return jsonify({
        "city": canonical_city,
        "origin": session["home_location"],
        "brief_rows": brief_rows,
        "city_blurb": city_blurb,
        "age_bracket": age_bracket,
        "recommendation": recommendation,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=False)

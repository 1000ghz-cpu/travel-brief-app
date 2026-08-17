#!/usr/bin/env python3
"""Flask web app for the travel brief: weather + USD exchange rate + air quality for a city.

Reuses the API logic from travelbrief.py. Air quality requires an
OpenWeatherMap API key in the OPENWEATHER_API_KEY environment variable
(get one at https://openweathermap.org/api). If an origin city is given,
the great-circle distance to the destination and a rough estimated fare
are shown alongside the rest of the brief.

Example usage:
    python3 app.py
    # then open http://127.0.0.1:5001 in a browser

    OPENWEATHER_API_KEY=your_key_here python3 app.py
"""
import math
import os

import requests
from flask import Flask, render_template, request

from travelbrief import build_brief, geocode_city

app = Flask(__name__)

EARTH_RADIUS_KM = 6371.0
FARE_PER_KM = 0.12
MINIMUM_FARE = 40.0

# Label (as produced by build_brief) -> icon shown next to it in the result card.
BRIEF_ICONS = {
    "Location": "📍",
    "Weather": "🌤️",
    "Temperature": "🌡️",
    "Wind speed": "💨",
    "Exchange rate": "💱",
    "Air quality": "🌬️",
}
DEFAULT_BRIEF_ICON = "•"

# Age bracket -> (min, max) inclusive; max of None means no upper bound.
AGE_RECOMMENDATIONS = {
    (18, 25): {
        "style": "Budget-friendly adventure and social travel",
        "activities": ["music festivals", "hostels", "nightlife", "backpacking"],
    },
    (26, 40): {
        "style": "Active, experience-driven travel",
        "activities": ["food tours", "hiking", "boutique hotels", "local nightlife"],
    },
    (41, 60): {
        "style": "Comfort-focused cultural travel",
        "activities": ["monuments", "museums", "wine tasting", "mid-range hotels"],
    },
    (61, None): {
        "style": "Relaxed, low-strain sightseeing",
        "activities": ["guided tours", "monuments", "relaxed sightseeing", "cruises"],
    },
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in kilometers."""
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = (math.radians(v) for v in (lat1, lon1, lat2, lon2))
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def estimate_fare(distance_km):
    """Rough distance-based fare estimate — not live pricing."""
    return max(MINIMUM_FARE, distance_km * FARE_PER_KM)


def get_age_recommendation(age):
    """Return the recommendation dict for the age bracket containing `age`, or None."""
    for (low, high), recommendation in AGE_RECOMMENDATIONS.items():
        if age >= low and (high is None or age <= high):
            return recommendation
    return None


def parse_brief(brief_text):
    """Split build_brief's "Title\\n----\\nLabel: value\\n..." text into a title and rows."""
    lines = brief_text.splitlines()
    title = lines[0]
    rows = []
    for line in lines[2:]:
        label, _, value = line.partition(": ")
        rows.append({"icon": BRIEF_ICONS.get(label, DEFAULT_BRIEF_ICON), "label": label, "value": value})
    return title, rows


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", error=None)


@app.route("/brief", methods=["POST"])
def brief():
    city = request.form.get("city", "").strip()
    age = request.form.get("age", "").strip()
    origin_city = request.form.get("origin_city", "").strip()

    if not city or not age.isdigit():
        return render_template("index.html", error="Please enter a city name and a valid age."), 400

    openweather_api_key = os.environ.get("OPENWEATHER_API_KEY")

    try:
        result = build_brief(city, openweather_api_key)
    except requests.RequestException as exc:
        return render_template("index.html", error=f"Network error while fetching travel brief: {exc}"), 502

    if result is None:
        return render_template("index.html", error=f"Could not find a city named '{city}'."), 404

    brief_title, brief_rows = parse_brief(result)
    recommendation = get_age_recommendation(int(age))

    if origin_city:
        try:
            origin_place = geocode_city(origin_city)
            destination_place = geocode_city(city)
        except requests.RequestException as exc:
            return render_template("index.html", error=f"Network error while calculating distance: {exc}"), 502

        if origin_place is None:
            return render_template("index.html", error=f"Could not find a city named '{origin_city}'."), 404

        distance_km = haversine_km(
            origin_place["latitude"], origin_place["longitude"],
            destination_place["latitude"], destination_place["longitude"],
        )
        brief_rows.append({"icon": "📏", "label": "Distance from origin", "value": f"{distance_km:.0f} km"})
        brief_rows.append({
            "icon": "💵",
            "label": "Estimated fare — rough approximation, not live pricing",
            "value": f"${estimate_fare(distance_km):.2f}",
        })

    return render_template(
        "result.html",
        city=city,
        age=age,
        brief_title=brief_title,
        brief_rows=brief_rows,
        recommendation=recommendation,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)

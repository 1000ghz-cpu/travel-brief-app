#!/usr/bin/env python3
"""Flask web app for the travel brief: weather + USD exchange rate + air quality for a city.

Reuses the API logic from travelbrief.py. Air quality requires an
OpenWeatherMap API key in the OPENWEATHER_API_KEY environment variable
(get one at https://openweathermap.org/api).

Example usage:
    python3 app.py
    # then open http://127.0.0.1:5001 in a browser

    OPENWEATHER_API_KEY=your_key_here python3 app.py
"""
import os

import requests
from flask import Flask, render_template_string, request

from travelbrief import build_brief

app = Flask(__name__)

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


def get_age_recommendation(age):
    """Return the recommendation dict for the age bracket containing `age`, or None."""
    for (low, high), recommendation in AGE_RECOMMENDATIONS.items():
        if age >= low and (high is None or age <= high):
            return recommendation
    return None


FORM_TEMPLATE = """
<!doctype html>
<html>
<head><title>Travel Brief</title></head>
<body>
<h1>Travel Brief</h1>
<form method="post" action="/brief">
  <label for="city">City name:</label>
  <input type="text" id="city" name="city" required>
  <br><br>
  <label for="age">Age:</label>
  <input type="number" id="age" name="age" min="0" required>
  <br><br>
  <button type="submit">Get brief</button>
</form>
{% if error %}<p style="color: red;">{{ error }}</p>{% endif %}
</body>
</html>
"""

RESULT_TEMPLATE = """
<!doctype html>
<html>
<head><title>Travel Brief for {{ city }}</title></head>
<body>
<h1>Travel Brief for {{ city }} (age {{ age }})</h1>
<pre>{{ brief }}</pre>
{% if recommendation %}
<h2>Travel style for your age</h2>
<p>{{ recommendation.style }}</p>
<ul>
{% for activity in recommendation.activities %}
  <li>{{ activity }}</li>
{% endfor %}
</ul>
{% endif %}
<p><a href="/">Back</a></p>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(FORM_TEMPLATE, error=None)


@app.route("/brief", methods=["POST"])
def brief():
    city = request.form.get("city", "").strip()
    age = request.form.get("age", "").strip()

    if not city or not age.isdigit():
        return render_template_string(FORM_TEMPLATE, error="Please enter a city name and a valid age."), 400

    openweather_api_key = os.environ.get("OPENWEATHER_API_KEY")

    try:
        result = build_brief(city, openweather_api_key)
    except requests.RequestException as exc:
        return render_template_string(FORM_TEMPLATE, error=f"Network error while fetching travel brief: {exc}"), 502

    if result is None:
        return render_template_string(FORM_TEMPLATE, error=f"Could not find a city named '{city}'."), 404

    recommendation = get_age_recommendation(int(age))

    return render_template_string(
        RESULT_TEMPLATE, city=city, age=age, brief=result, recommendation=recommendation
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)

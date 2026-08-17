#!/usr/bin/env python3
"""Flask web app for the travel brief: weather + USD exchange rate + air quality for a city.

Reuses the API logic from travelbrief.py. Air quality requires an
OpenWeatherMap API key in the OPENWEATHER_API_KEY environment variable
(get one at https://openweathermap.org/api).

Example usage:
    python3 app.py
    # then open http://127.0.0.1:5000 in a browser

    OPENWEATHER_API_KEY=your_key_here python3 app.py
"""
import os

import requests
from flask import Flask, render_template_string, request

from travelbrief import build_brief

app = Flask(__name__)

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

    return render_template_string(RESULT_TEMPLATE, city=city, age=age, brief=result)


if __name__ == "__main__":
    app.run(debug=True)

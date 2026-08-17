#!/usr/bin/env python3
"""Command-line travel briefing: weather + USD exchange rate for a city.

Example usage:
    python3 travelbrief.py Tokyo
    python3 travelbrief.py "New York"
"""
import argparse
import sys

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
EXCHANGE_URL = "https://api.frankfurter.dev/v1/latest"

WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# ISO 3166-1 alpha-2 country code -> ISO 4217 currency code.
COUNTRY_TO_CURRENCY = {
    "US": "USD", "CA": "CAD", "MX": "MXN", "BR": "BRL", "AR": "ARS",
    "GB": "GBP", "IE": "EUR", "FR": "EUR", "DE": "EUR", "ES": "EUR",
    "IT": "EUR", "PT": "EUR", "NL": "EUR", "BE": "EUR", "AT": "EUR",
    "GR": "EUR", "FI": "EUR", "LU": "EUR", "SK": "EUR", "SI": "EUR",
    "EE": "EUR", "LV": "EUR", "LT": "EUR", "CY": "EUR", "MT": "EUR",
    "HR": "EUR", "CH": "CHF", "NO": "NOK", "SE": "SEK", "DK": "DKK",
    "IS": "ISK", "PL": "PLN", "CZ": "CZK", "HU": "HUF", "RO": "RON",
    "BG": "BGN", "RU": "RUB", "UA": "UAH", "TR": "TRY", "IL": "ILS",
    "SA": "SAR", "AE": "AED", "QA": "QAR", "KW": "KWD", "BH": "BHD",
    "OM": "OMR", "JO": "JOD", "EG": "EGP", "ZA": "ZAR", "NG": "NGN",
    "KE": "KES", "GH": "GHS", "MA": "MAD", "IN": "INR", "PK": "PKR",
    "BD": "BDT", "LK": "LKR", "NP": "NPR", "CN": "CNY", "JP": "JPY",
    "KR": "KRW", "TW": "TWD", "HK": "HKD", "SG": "SGD", "MY": "MYR",
    "TH": "THB", "VN": "VND", "PH": "PHP", "ID": "IDR", "AU": "AUD",
    "NZ": "NZD", "FJ": "FJD", "CL": "CLP", "CO": "COP", "PE": "PEN",
    "UY": "UYU", "PY": "PYG", "BO": "BOB", "VE": "VES", "EC": "USD",
    "PA": "USD", "CR": "CRC", "GT": "GTQ", "DO": "DOP", "JM": "JMD",
    "TT": "TTD",
}

WMO_UNKNOWN_CODE_DESC = "Unknown conditions"


def geocode_city(city):
    response = requests.get(GEOCODING_URL, params={"name": city, "count": 1}, timeout=10)
    response.raise_for_status()
    data = response.json()
    results = data.get("results")
    if not results:
        return None
    return results[0]


def get_current_weather(latitude, longitude, timezone):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "timezone": timezone,
    }
    response = requests.get(FORECAST_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json().get("current", {})


def get_exchange_rate(currency_code):
    if currency_code == "USD":
        return 1.0
    response = requests.get(EXCHANGE_URL, params={"base": "USD", "symbols": currency_code}, timeout=10)
    response.raise_for_status()
    rates = response.json().get("rates", {})
    return rates.get(currency_code)


def build_brief(city_name):
    place = geocode_city(city_name)
    if place is None:
        return None

    latitude = place["latitude"]
    longitude = place["longitude"]
    timezone = place.get("timezone", "auto")
    country = place.get("country", "Unknown country")
    country_code = place.get("country_code", "")

    weather = get_current_weather(latitude, longitude, timezone)
    weather_code = weather.get("weather_code")
    weather_desc = WMO_WEATHER_CODES.get(weather_code, WMO_UNKNOWN_CODE_DESC)

    currency_code = COUNTRY_TO_CURRENCY.get(country_code)
    exchange_rate = get_exchange_rate(currency_code) if currency_code else None

    lines = [
        f"Travel Brief: {place['name']}, {country}",
        "-" * 40,
        f"Location: {latitude:.2f}, {longitude:.2f} ({timezone})",
        f"Weather: {weather_desc}",
        f"Temperature: {weather.get('temperature_2m', 'N/A')}°C",
        f"Wind speed: {weather.get('wind_speed_10m', 'N/A')} km/h",
    ]

    if currency_code and exchange_rate is not None:
        lines.append(f"Exchange rate: 1 USD = {exchange_rate:.2f} {currency_code}")
    elif currency_code:
        lines.append(f"Exchange rate: unavailable for {currency_code}")
    else:
        lines.append("Exchange rate: unknown currency for this country")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Print a weather + currency travel brief for a city.")
    parser.add_argument("city", help="City name, e.g. 'Tokyo' or 'New York'")
    args = parser.parse_args()

    try:
        brief = build_brief(args.city)
    except requests.RequestException as exc:
        print(f"Network error while fetching travel brief: {exc}", file=sys.stderr)
        sys.exit(1)

    if brief is None:
        print(f"Could not find a city named '{args.city}'.")
        sys.exit(1)

    print(brief)


if __name__ == "__main__":
    main()

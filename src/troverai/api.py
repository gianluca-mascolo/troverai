"""API layer for TroveRAI - handles HTTP requests to RaiPlay."""

import json
import sys

import requests

PALINSESTO_URL = "https://www.raiplay.it/palinsesto/app"
CHANNELS_URL = "https://www.raiplay.it/guidatv.json"

# Module-level session
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
})


def fetch_schedule(channel, date):
    """Fetch schedule for a specific channel and date."""
    url = f"{PALINSESTO_URL}/{channel}/{date}.json"

    response = SESSION.get(url)

    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code} for {url}", file=sys.stderr)
        return None

    try:
        return response.json()
    except json.JSONDecodeError:
        print("Error: Invalid JSON response", file=sys.stderr)
        return None


def fetch_channels():
    """Fetch list of available channels."""
    response = SESSION.get(CHANNELS_URL)

    if response.status_code != 200:
        return None

    return response.json()

"""Client for the World Bank Open Data API (v2)."""
import logging

import requests

BASE_URL = "https://api.worldbank.org/v2"

logger = logging.getLogger(__name__)


def fetch_indicator_value(country_code, indicator_code, year):
    """
    Fetches value of an indicator for a given country and year.
    Returns None if the API is slow, unavailable, or has no value for that year.
    """

    url = f"{BASE_URL}/country/{country_code}/indicator/{indicator_code}"
    params = {
        "format": "json",
        "date": str(year),
        "per_page": 1     # speeds up response dramatically
    }

    try:
        resp = requests.get(url, params=params, timeout=25)
    except requests.exceptions.Timeout:
        logger.warning("World Bank API timeout")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning("World Bank API error: %s", e)
        return None

    if not resp.ok:
        logger.warning("World Bank API bad response: %s", resp.status_code)
        return None

    try:
        data = resp.json()
        records = data[1]       # second element contains the data array
        if not records:
            return None
        return records[0].get("value")
    except (ValueError, IndexError, KeyError, TypeError, AttributeError) as e:
        logger.warning("World Bank API parse error: %s", e)
        return None

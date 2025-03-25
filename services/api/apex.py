import logging
import requests
from typing import Optional, Dict
from urllib.parse import quote

from config.constants import APEX_PLATFORM_MAPPING
from config.settings import TRN_API_KEY
from core.errors import APIError, ResourceNotFoundError

logger = logging.getLogger(__name__)


def fetch_apex_stats(platform: str, name: str) -> Dict:
    """
    Fetch Apex Legends player stats from the TRN API.

    Args:
        platform: The platform (Xbox, Playstation, Origin)
        name: The player's username

    Returns:
        The player stats data

    Raises:
        ResourceNotFoundError: If the player is not found
        APIError: If there's an API error
        ValueError: If the platform is invalid
    """
    api_platform = APEX_PLATFORM_MAPPING.get(platform)
    if not api_platform:
        raise ValueError(f"Invalid platform: {platform}")

    name_encoded = quote(name)
    url = f"https://public-api.tracker.gg/v2/apex/standard/profile/{api_platform}/{name_encoded}"

    if not TRN_API_KEY:
        logger.error("API key not found. Please check your .env file.")
        raise APIError("API key not configured")

    headers = {"TRN-Api-Key": TRN_API_KEY}

    try:
        response = requests.get(url, headers=headers)
        status_code = response.status_code

        if status_code == 200:
            return response.json()
        elif status_code == 404:
            raise ResourceNotFoundError(f"No Apex Legends stats found for {name} on {platform}")
        elif status_code == 403:
            logger.error(
                f"Access forbidden (403) when fetching stats for {name} on {api_platform}."
            )
            raise APIError("Invalid API key or insufficient permissions")
        else:
            logger.error(
                f"Failed to fetch stats for {name} on {api_platform}. HTTP {status_code} received."
            )
            raise APIError(f"API returned status code {status_code}")

    except requests.RequestException as e:
        logger.error(f"Request error occurred: {e}", exc_info=True)
        raise APIError(f"Request error: {str(e)}")


def get_percentile_label(percentile: Optional[float]) -> str:
    """Get a label for a percentile value."""
    if percentile is None:
        return 'N/A'
    if percentile >= 90:
        return '🌟 Top'
    return 'Top' if percentile >= 50 else 'Bottom'


def format_stat_value(stat_data: Dict) -> str:
    """Format a stat value with percentile."""
    stat_value = stat_data.get('value')
    if stat_value is not None:
        percentile_label = get_percentile_label(stat_data.get('percentile', 0))
        percentile_value = int(stat_data.get('percentile', 0)) if percentile_label != 'N/A' else 0
        return f"{int(stat_value):,} ({percentile_label} {percentile_value}%)"
    return 'N/A'
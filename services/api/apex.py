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


def get_formatted_percentile(percentile: Optional[float]) -> str:
    """
    Get a formatted string for a percentile value.
    
    If percentile >= 50, it shows "Top X%" where X is (100 - percentile).
    If percentile < 50, it shows "Bottom X%" where X is the percentile.
    """
    if percentile is None:
        return 'N/A'
    
    if percentile >= 50:
        value = 100 - percentile
        # Use simple integer if it's a whole number close to integer, otherwise 1 decimal
        precision = 0 if value >= 1 and value % 1 == 0 else 1
        formatted_value = f"{value:.{precision}f}".rstrip('0').rstrip('.') if precision > 0 else f"{int(value)}"
        
        # Special case for 100th percentile (0% top) -> Top 0.1% or similar to avoid "Top 0%" if not precise
        if formatted_value == '0':
             formatted_value = '0.1' 

        return f"Top {formatted_value}%"
    else:
        # Bottom X%
        formatted_value = f"{int(percentile)}"
        return f"Bottom {formatted_value}%"


def format_stat_value(stat_data: Dict) -> str:
    """Format a stat value with percentile."""
    stat_value = stat_data.get('value')
    if stat_value is not None:
        percentile = stat_data.get('percentile')
        percentile_str = get_formatted_percentile(percentile)
        
        if percentile_str != 'N/A':
            return f"{int(stat_value):,} ({percentile_str})"
        return f"{int(stat_value):,}"
    return 'N/A'
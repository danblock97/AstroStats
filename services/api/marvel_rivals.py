import logging
from typing import Dict
from urllib.parse import quote

import aiohttp

from config.constants import MARVEL_RIVALS_CURRENT_SEASON
from config.settings import MARVEL_RIVALS_API_KEY
from core.errors import APIError, ResourceNotFoundError

logger = logging.getLogger(__name__)


async def fetch_marvel_rivals_player(name: str, season: int = MARVEL_RIVALS_CURRENT_SEASON) -> Dict:
    """Fetch Marvel Rivals player stats."""
    if not MARVEL_RIVALS_API_KEY:
        logger.error("Marvel Rivals API key not found. Please check your .env file.")
        raise APIError("Marvel Rivals API key not configured")

    encoded_name = quote(name)
    url = f"https://marvelrivalsapi.com/api/v1/player/{encoded_name}?season={season}"
    headers = {"x-api-key": MARVEL_RIVALS_API_KEY}

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, headers=headers) as response:
                status_code = response.status
                if status_code == 200:
                    return await response.json()
                if status_code == 404:
                    raise ResourceNotFoundError(f"No Marvel Rivals stats found for {name}")
                if status_code in (401, 403):
                    raise APIError("Invalid Marvel Rivals API key or insufficient permissions")

                body = await response.text()
                logger.error(
                    "Failed to fetch Marvel Rivals stats for %s. HTTP %s. Body: %s",
                    name,
                    status_code,
                    body[:300],
                )
                raise APIError(f"Marvel Rivals API returned status code {status_code}")
        except aiohttp.ClientError as e:
            logger.error("Request error while fetching Marvel Rivals stats: %s", e, exc_info=True)
            raise APIError("Failed to connect to Marvel Rivals API") from e
        except TimeoutError as e:
            logger.error("Timeout while fetching Marvel Rivals stats: %s", e, exc_info=True)
            raise APIError("Marvel Rivals API request timed out") from e

import os
import logging
import datetime
from typing import Optional

import discord

logger = logging.getLogger(__name__)

async def get_conditional_embed(interaction: discord.Interaction, embed_key: str, default_color: discord.Color) -> Optional[discord.Embed]:
    """Get a conditional embed based on an environment variable."""
    embed_content = os.getenv(embed_key)
    if embed_content:
        embed = discord.Embed(
            description=embed_content,
            color=default_color
        )
        return embed
    return None

def create_timestamp() -> datetime.datetime:
    """Create a timestamp in UTC for embed footers, etc."""
    return datetime.datetime.now(datetime.timezone.utc)

def create_progress_bar(current: int, total: int, length: int = 10, fill_char: str = "█", empty_char: str = "░") -> str:
    """Create a text progress bar."""
    if total <= 0:
        total = 1  # Avoid division by zero
    filled_length = int(length * current / total)
    bar = fill_char * filled_length + empty_char * (length - filled_length)
    return bar

def handle_api_error(error, context_msg: str = "API Error"):
    """Handle API errors more gracefully in logs.
    
    Args:
        error: The error object
        context_msg: Context message about what operation was being performed
    """
    if hasattr(error, 'status') and error.status:
        logger.error(f"{context_msg}: HTTP {error.status}")
    else:
        logger.error(f"{context_msg}: {type(error).__name__}")
    
    # If it's a topgg ServerError, handle it specially
    if type(error).__name__ == "ServerError" and hasattr(error, 'status'):
        # Don't log the entire HTML response, just the status code
        logger.error(f"Top.gg server error (status code: {error.status}). This is likely a temporary issue with Top.gg's servers.")
        return
        
    # For other errors, log the error message but limit it
    error_str = str(error)
    if len(error_str) > 200:  # Limit very long error messages
        logger.error(f"Error details (truncated): {error_str[:200]}...")
    else:
        logger.error(f"Error details: {error_str}")
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
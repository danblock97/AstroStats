import os
import discord
from typing import Optional

async def get_conditional_embed(interaction: discord.Interaction, embed_key: str, default_color: discord.Color) -> Optional[discord.Embed]:
    embed_content = os.getenv(embed_key)
    if embed_content:
        embed = discord.Embed(
            description=embed_content,
            color=default_color
        )
        return embed
    return None

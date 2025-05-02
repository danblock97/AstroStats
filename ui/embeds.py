import datetime
import discord
from typing import Optional, Dict

def create_base_embed(title: str, description: Optional[str] = None, color: discord.Color = discord.Color.blue(),
                     url: Optional[str] = None) -> discord.Embed:
    """Create a base embed with common settings."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        url=url,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_footer(text="Built By Goldiez ❤️ Support: astrostats.info")
    return embed

def add_support_field(embed: discord.Embed) -> discord.Embed:
    """Add a support field to an embed."""
    embed.add_field(
        name="Support Us ❤️",
        value="[If you enjoy using this bot, consider supporting us!](https://astrostats.info)",
        inline=False
    )
    return embed

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create an error embed."""
    embed = create_base_embed(title, description, discord.Color.red())
    return embed

def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create a success embed."""
    embed = create_base_embed(title, description, discord.Color.green())
    return embed

def add_fields_from_dict(embed: discord.Embed, fields_dict: Dict[str, str], inline: bool = True) -> discord.Embed:
    """Add multiple fields to an embed from a dictionary."""
    for name, value in fields_dict.items():
        embed.add_field(name=name, value=value, inline=inline)
    return embed

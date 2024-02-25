import discord
import datetime
import requests
from typing import Literal
import os

PLATFORM_MAPPING = {
    'Xbox': 'xbl',
    'Playstation': 'psn',
    'Origin (PC)': 'origin',
}

async def Apex(interaction: discord.Interaction, platform: Literal['Xbox', 'Playstation', 'Origin (PC)'], name: str = None):
    format
    if name is None:
        await interaction.response.send_message("`/Apex <username>`")
        return
    if platform is None:
        await interaction.response.send_message("`/Apex <Xbox/Playstation/Origin>`")
        return

    api_platform = PLATFORM_MAPPING.get(platform)
    if not api_platform:
        await interaction.response.send_message("Invalid platform. Please use Xbox, Playstation, or Origin.")
        return

    response = requests.get(f"https://public-api.tracker.gg/v2/apex/standard/profile/{api_platform}/{name}",
                            headers={"TRN-Api-Key": os.getenv('TRN-Api-Key')})

    if response.status_code == 200:
        data = response.json()
        segments = data['data']['segments'][0]
        stats = segments['stats']

        embed = discord.Embed(title=f"Apex Legends - Lifetime Overview",
                              url=f"https://apex.tracker.gg/apex/profile/{api_platform}/{name}", color=0xdd4f7a)

        for key, value in stats.items():
            if isinstance(value, dict):
                embed.add_field(
                    name=value['displayName'], value=value['displayValue'], inline=True)
            embed.timestamp = datetime.datetime.utcnow()
            embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Failed to retrieve your Apex stats. Please ensure your name matches what you see in the game, and the platform matches the platform you play on.")

def setup(client):
    client.tree.command(name="apex", description="Lists all available commands")(Apex)
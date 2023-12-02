import discord
import datetime
import requests
import os

async def apex(interaction: discord.Interaction, name: str = None, platform: str = None):
    if name is None:
        await interaction.response.send_message("`/apex <username>`")
        return
    if platform is None:
        await interaction.response.send_message("`/apex <xbl/psn/origin>`")
        return

    response = requests.get(f"https://public-api.tracker.gg/v2/apex/standard/profile/{platform}/{name}",
                            headers={"TRN-Api-Key": os.getenv('TRN-Api-Key')})

    if response.status_code == 200:
        data = response.json()
        segments = data['data']['segments'][0]
        stats = segments['stats']

        embed = discord.Embed(title=f"Apex Legends - Lifetime Overview",
                              url=f"https://apex.tracker.gg/apex/profile/{platform}/{name}", color=0xdd4f7a)

        for key, value in stats.items():
            if isinstance(value, dict):
                embed.add_field(
                    name=value['displayName'], value=value['displayValue'], inline=True)
            embed.timestamp = datetime.datetime.utcnow()
            embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Failed to retrieve your Apex stats. The TRN API is Currently Unavailable")

def setup(client):
    client.tree.command(name="apex", description="Check your Apex Lifetime Stats")(apex)

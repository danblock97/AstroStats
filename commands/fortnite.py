import discord
import datetime
from typing import Literal, Optional, Dict
import os
import aiohttp
import logging

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Time Range Mapping
TIME_MAPPING = {
    'Season': 'season',
    'Lifetime': 'lifetime',
}

# Helper function to retrieve Fortnite stats from the API
async def fetch_fortnite_stats(name: str, time_window: str) -> Optional[Dict]:
    url = f"https://fortnite-api.com/v2/stats/br/v2?timeWindow={time_window}&name={name}"
    headers = {"Authorization": os.getenv('FORTNITE_API_KEY')}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    # Account not found, skip logging
                    return None
                else:
                    # Log any other non-200, non-404 status codes
                    logger.error(f"Failed to fetch stats for {name}: {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Client error occurred: {e}")
            return None

# Helper function to send an error embed
async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=f"{description}\n\nFor more assistance, visit [AstroStats Support](https://astrostats.vercel.app)",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    await interaction.response.send_message(embed=embed)

# Main Fortnite command
@discord.app_commands.command(name="fortnite", description="Check your Fortnite Player Stats")
async def fortnite(interaction: discord.Interaction, time: Literal['Season', 'Lifetime'], name: str = None):
    try:
        # Validate input
        if not name:
            await send_error_embed(interaction, "Missing Username", "You need to provide a username for the stats.")
            return

        time_window = TIME_MAPPING.get(time)

        # Fetch Fortnite stats from the API
        data = await fetch_fortnite_stats(name, time_window)
        if not data or 'data' not in data:
            await send_error_embed(
                interaction,
                "Account Not Found",
                f"No stats found for **{name}** for **{time_window}**. Please double-check your details. If you haven't played this season, be sure to play some games and try again later."
            )
            return

        stats = data['data']
        account = stats['account']
        battle_pass = stats['battlePass']

        # Calculate win rate
        wins = stats['stats']['all']['overall']['wins']
        matches = stats['stats']['all']['overall']['matches']
        calculated_win_rate = wins / matches if matches > 0 else 0

        # Build the embed message
        embed = build_embed(name, account, battle_pass, stats, calculated_win_rate)
        await interaction.response.send_message(embed=embed)

    except ValueError as e:
        logger.error(f"Validation Error: {e}")
        await send_error_embed(interaction, "Validation Error", str(e))

    except (KeyError, ValueError) as e:
        logger.error(f"Data Error: {e}")
        await send_error_embed(interaction, "Data Error", "Failed to retrieve valid Fortnite stats. Please try again later.")

    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        await send_error_embed(interaction, "Unexpected Error", "An unexpected error occurred. Please try again later.")

# Function to build the embed message
def build_embed(name: str, account: Dict, battle_pass: Dict, stats: Dict, calculated_win_rate: float) -> discord.Embed:
    embed = discord.Embed(
        title=f"Fortnite - {name}",
        color=0xdd4f7a,
        url=f"https://fortnitetracker.com/profile/all/{name}"
    )
    embed.set_thumbnail(url="https://seeklogo.com/images/F/fortnite-logo-1F7897BD1E-seeklogo.com.png")

    # Account and match information
    embed.add_field(name="Account", value=f"Name: {account['name']}\nLevel: {battle_pass['level']}", inline=True)
    embed.add_field(name="Match Placements",
                    value=f"Victory Royales: {stats['stats']['all']['overall']['wins']} \nTop 5: {stats['stats']['all']['overall']['top5']}\nTop 12: {stats['stats']['all']['overall']['top12']}",
                    inline=True)

    # Kill statistics
    embed.add_field(name="Kill Stats",
                    value=f"Kills/Deaths: {stats['stats']['all']['overall']['kills']:,}/{stats['stats']['all']['overall']['deaths']:,}\n"
                          f"KD Ratio: {stats['stats']['all']['overall']['kd']:.2f}\n"
                          f"Kills Per Minute: {stats['stats']['all']['overall']['killsPerMin']:.2f}\n"
                          f"Kills Per Match: {stats['stats']['all']['overall']['killsPerMatch']:.2f}\n"
                          f"Players Outlived: {stats['stats']['all']['overall']['playersOutlived']:,}",
                    inline=False)

    # Match statistics
    embed.add_field(name="Match Stats",
                    value=f"Total Matches Played: {stats['stats']['all']['overall']['matches']:,}\n"
                          f"Win Rate: {calculated_win_rate:.2%}\n"
                          f"Total Score: {stats['stats']['all']['overall']['score']:,}\n"
                          f"Score Per Minute: {stats['stats']['all']['overall']['scorePerMin']:.0f}\n"
                          f"Score Per Match: {stats['stats']['all']['overall']['scorePerMatch']:.0f}\n"
                          f"Total Minutes Played: {stats['stats']['all']['overall']['minutesPlayed']:,}",
                    inline=True)

    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")
    return embed

# Setup function for the bot
async def setup(client: discord.Client):
    client.tree.add_command(fortnite)

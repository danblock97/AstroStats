import discord
import datetime
from typing import Literal, Optional, Dict
import os
import aiohttp
import logging
import urllib.parse

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Time Range Mapping
TIME_MAPPING = {
    'Season': 'season',
    'Lifetime': 'lifetime',
}

# Helper function to retrieve Fortnite stats from the API
async def fetch_fortnite_stats(name: str, time_window: str) -> Optional[Dict]:
    """
    Fetch Fortnite stats from fortnite-api.com using aiohttp.
    Logs errors and warnings to console for the developer, returns JSON or None.
    """
    url = f"https://fortnite-api.com/v2/stats/br/v2?timeWindow={time_window}&name={name}"
    api_key = os.getenv('FORTNITE_API_KEY')
    if not api_key:
        # Log error for developer if the key is missing.
        logger.error("Fortnite API key not found. Please check your .env file.")
        return None

    headers = {"Authorization": api_key}
    # Optional debug log for successful requests:
    # logger.debug(f"Fetching Fortnite stats from URL: {url}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                status = response.status
                if status == 200:
                    # Success, optionally log debug or nothing
                    return await response.json()
                elif status == 404:
                    # Log a warning so you can see in the console that no data was found
                    logger.warning(
                        f"No data found (404) for username: {name} (time_window={time_window})."
                    )
                    return None
                else:
                    # Non-200, non-404 response => log as an error
                    logger.error(f"Failed to fetch stats for {name}. HTTP {status} received.")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Client error occurred while fetching Fortnite stats: {e}", exc_info=True)
            return None

# Helper function to send an error embed
async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    """
    Sends a red-embedded error message to the user.
    """
    embed = discord.Embed(
        title=title,
        description=f"{description}\n\nFor more assistance, visit [AstroStats Support](https://astrostats.vercel.app)",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    await interaction.response.send_message(embed=embed)

# Main Fortnite command
@discord.app_commands.command(name="fortnite", description="Check your Fortnite Player Stats")
async def fortnite(
    interaction: discord.Interaction,
    time: Literal['Season', 'Lifetime'],
    name: str = None
):
    """
    Slash command for retrieving Fortnite stats based on time window (season/lifetime).
    """
    try:
        # Validate input
        if not name:
            await send_error_embed(
                interaction,
                "Missing Username",
                "You need to provide a username for the stats."
            )
            return

        time_window = TIME_MAPPING.get(time)

        # Fetch Fortnite stats from the API
        data = await fetch_fortnite_stats(name, time_window)
        # If data is None or does not contain 'data' key, assume account not found or invalid data
        if not data or 'data' not in data:
            await send_error_embed(
                interaction,
                "Account Not Found",
                (
                    f"No stats found for **{name}** for the current season. "
                    "Epic may not have updated your stats yet! Please double-check your details. "
                    "If you haven't played this season, be sure to play some games and try again later."
                )
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
        logger.error(f"Validation Error: {e}", exc_info=True)
        await send_error_embed(interaction, "Validation Error", str(e))

    except KeyError as e:
        logger.error(f"Data Error: Missing key in response: {e}", exc_info=True)
        await send_error_embed(
            interaction,
            "Data Error",
            "Failed to retrieve valid Fortnite stats. Please try again later."
        )

    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)
        await send_error_embed(
            interaction,
            "Unexpected Error",
            "An unexpected error occurred. Please try again later."
        )

# Slash-command-specific error handler
@fortnite.error
async def fortnite_error_handler(
    interaction: discord.Interaction,
    error: discord.app_commands.AppCommandError
):
    """
    Catch-all error handler for the /fortnite command.
    Logs full traceback to console, sends a friendly embed to the user.
    """
    logger.error(f"An error occurred in /fortnite command: {error}", exc_info=True)

    embed = discord.Embed(
        title="Command Error",
        description="An error occurred while executing the /fortnite command. Please try again later.",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")

    # If we've already responded, send a follow-up
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)

# Global Event Error Handler (optional)
async def on_error(event_method, *args, **kwargs):
    logger.exception(f"An error occurred in the event: {event_method}", exc_info=True)

# Function to build the embed message
def build_embed(name: str, account: Dict, battle_pass: Dict, stats: Dict, calculated_win_rate: float) -> discord.Embed:
    encoded_name = urllib.parse.quote(name)
    embed = discord.Embed(
        title=f"Fortnite - {name}",
        color=0xdd4f7a,
        url=f"https://fortnitetracker.com/profile/all/{encoded_name}"
    )
    embed.set_thumbnail(url="https://seeklogo.com/images/F/fortnite-logo-1F7897BD1E-seeklogo.com.png")

    # Account and match information
    embed.add_field(
        name="Account",
        value=f"Name: {account['name']}\nLevel: {battle_pass['level']}",
        inline=True
    )

    embed.add_field(
        name="Match Placements",
        value=(
            f"Victory Royales: {stats['stats']['all']['overall']['wins']}\n"
            f"Top 5: {stats['stats']['all']['overall']['top5']}\n"
            f"Top 12: {stats['stats']['all']['overall']['top12']}"
        ),
        inline=True
    )

    # Kill statistics
    embed.add_field(
        name="Kill Stats",
        value=(
            f"Kills/Deaths: {stats['stats']['all']['overall']['kills']:,}/"
            f"{stats['stats']['all']['overall']['deaths']:,}\n"
            f"KD Ratio: {stats['stats']['all']['overall']['kd']:.2f}\n"
            f"Kills Per Minute: {stats['stats']['all']['overall']['killsPerMin']:.2f}\n"
            f"Kills Per Match: {stats['stats']['all']['overall']['killsPerMatch']:.2f}\n"
            f"Players Outlived: {stats['stats']['all']['overall']['playersOutlived']:,}"
        ),
        inline=False
    )

    # Match statistics
    embed.add_field(
        name="Match Stats",
        value=(
            f"Total Matches Played: {stats['stats']['all']['overall']['matches']:,}\n"
            f"Win Rate: {calculated_win_rate:.2%}\n"
            f"Total Score: {stats['stats']['all']['overall']['score']:,}\n"
            f"Score Per Minute: {stats['stats']['all']['overall']['scorePerMin']:.0f}\n"
            f"Score Per Match: {stats['stats']['all']['overall']['scorePerMatch']:.0f}\n"
            f"Total Minutes Played: {stats['stats']['all']['overall']['minutesPlayed']:,}"
        ),
        inline=False
    )

    embed.add_field(
        name="Support Us ❤️",
        value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)"
    )

    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")
    return embed

# Setup function for the bot
async def setup(client: discord.Client):
    """
    Registers the /fortnite command and attaches the global event error handler.
    """
    client.tree.add_command(fortnite)
    client.event(on_error)

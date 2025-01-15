import os
import logging
import datetime
import urllib.parse
from typing import Literal, Optional, Dict

import discord
import aiohttp

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)

TIME_MAPPING = {
    'Season': 'season',
    'Lifetime': 'lifetime',
}

async def fetch_fortnite_stats(name: str, time_window: str) -> Optional[Dict]:
    api_key = os.getenv('FORTNITE_API_KEY')
    if not api_key:
        logger.error("Fortnite API key not found. Please check your .env file.")
        return None

    url = (
        "https://fortnite-api.com/v2/stats/br/v2"
        f"?timeWindow={time_window}&name={name}"
    )
    headers = {"Authorization": api_key}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                status = response.status
                if status == 200:
                    return await response.json()
                elif status == 404:
                    logger.warning(
                        f"No data found (404) for username: {name} (time_window={time_window})."
                    )
                    return None
                else:
                    logger.error(
                        f"Failed to fetch stats for {name}. HTTP {status} received."
                    )
                    return None
        except aiohttp.ClientError as e:
            logger.error(
                f"Client error occurred while fetching Fortnite stats: {e}",
                exc_info=True
            )
            return None

async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=(
            f"{description}\n\nFor more assistance, visit "
            "[AstroStats Support](https://astrostats.vercel.app)"
        ),
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    await interaction.response.send_message(embed=embed)

@discord.app_commands.command(name="fortnite", description="Check your Fortnite Player Stats")
async def fortnite(
    interaction: discord.Interaction,
    time: Literal['Season', 'Lifetime'],
    name: str = None
):
    try:
        if not name:
            await send_error_embed(
                interaction,
                "Missing Username",
                "You need to provide a username for the stats."
            )
            return

        time_window = TIME_MAPPING.get(time)
        data = await fetch_fortnite_stats(name, time_window)

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

        wins = stats['stats']['all']['overall']['wins']
        matches = stats['stats']['all']['overall']['matches']
        calculated_win_rate = wins / matches if matches > 0 else 0

        embed = build_embed(name, account, battle_pass, stats, calculated_win_rate)
        
        # Create the promotional embed
        promo_embed = discord.Embed(
            description="⭐ **New:** Squib Games Has Arrived to AstroStats! Check out `/help` for more information!",
            color=discord.Color.blue(),  # You can choose any color you prefer
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        promo_embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")

        # Send both embeds together
        await interaction.response.send_message(embeds=[embed, promo_embed])

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

@fortnite.error
async def fortnite_error_handler(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    logger.error(f"An error occurred in /fortnite command: {error}", exc_info=True)
    embed = discord.Embed(
        title="Command Error",
        description="An error occurred while executing the /fortnite command. Please try again later.",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)

async def on_error(event_method, *args, **kwargs):
    logger.exception(f"An error occurred in the event: {event_method}", exc_info=True)

def build_embed(name: str, account: Dict, battle_pass: Dict, stats: Dict, calculated_win_rate: float) -> discord.Embed:
    encoded_name = urllib.parse.quote(name)
    embed = discord.Embed(
        title=f"Fortnite - {name}",
        color=0xdd4f7a,
        url=f"https://fortnitetracker.com/profile/all/{encoded_name}"
    )
    embed.set_thumbnail(
        url="https://seeklogo.com/images/F/fortnite-logo-1F7897BD1E-seeklogo.com.png"
    )

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

async def setup(client: discord.Client):
    client.tree.add_command(fortnite)
    client.event(on_error)

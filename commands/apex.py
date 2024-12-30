import discord
import datetime
from typing import Literal, Optional, Dict
import os
import requests  # Using requests instead of aiohttp
import logging
from urllib.parse import quote
from dotenv import load_dotenv
import asyncio  # Import asyncio to use asyncio.to_thread

# Load environment variables
load_dotenv()

# Initialize logger
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Platform Mapping Dictionary
PLATFORM_MAPPING = {
    'Xbox': 'xbl',
    'Playstation': 'psn',
    'Origin (PC)': 'origin',
}

# Synchronous function using requests
def fetch_apex_stats(api_platform: str, name: str) -> Optional[Dict]:
    name_encoded = quote(name)
    url = f"https://public-api.tracker.gg/v2/apex/standard/profile/{api_platform}/{name_encoded}"
    api_key = os.getenv('TRN_API_KEY')
    if not api_key:
        logger.error("API key not found. Please check your .env file.")
        return None

    headers = {"TRN-Api-Key": api_key}

    # Instead of info-level logging for every request,
    # you can do debug-level or no logging for 200 responses.
    # logger.debug(f"Fetching data from URL: {url}")
    # If you want no logging for 200 at all, remove or comment out the line above.

    try:
        response = requests.get(url, headers=headers)
        status_code = response.status_code

        if status_code == 200:
            # If you want to keep track of successful requests at debug level:
            # logger.debug(f"Successfully fetched stats for {name} on {api_platform}.")
            return response.json()

        elif status_code == 404:
            logger.warning(f"No data found (404) for {name} on {api_platform}.")
            return None

        elif status_code == 403:
            logger.error(
                f"Access forbidden (403) when fetching stats for {name} on {api_platform}."
            )
            raise PermissionError("Access forbidden: Invalid API key or insufficient permissions.")

        else:
            # Only log non-200 statuses at error or warning level
            logger.error(
                f"Failed to fetch stats for {name} on {api_platform}. HTTP {status_code} received."
            )
            return None

    except requests.RequestException as e:
        logger.error(f"Request error occurred: {e}", exc_info=True)
        return None

# Helper function to format percentile data
def get_percentile_label(percentile: Optional[float]) -> str:
    if percentile is None:
        return 'N/A'
    if percentile >= 90:
        return '🌟 Top'
    return 'Top' if percentile >= 50 else 'Bottom'

# Helper function to format the stat value with percentile
def format_stat_value(stat_data: Dict) -> str:
    stat_value = stat_data.get('value')
    if stat_value is not None:
        percentile_label = get_percentile_label(stat_data.get('percentile', 0))
        percentile_value = int(stat_data.get('percentile', 0)) if percentile_label != 'N/A' else 0
        return f"{int(stat_value):,} ({percentile_label} {percentile_value}%)"
    return 'N/A'

# Helper function to send an error embed to the user
async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=f"{description}\n\nFor more assistance, visit [AstroStats Support](https://astrostats.vercel.app)",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    await interaction.followup.send(embed=embed)

# Main Apex Legends command
@discord.app_commands.command(name="apex", description="Check your Apex Legends Player Stats")
async def apex(
    interaction: discord.Interaction,
    platform: Literal['Xbox', 'Playstation', 'Origin (PC)'],
    name: str
):
    try:
        # Defer the response to allow time for processing
        await interaction.response.defer()

        # Validate input
        if not name:
            await send_error_embed(
                interaction,
                "Missing Username",
                "You need to provide a username for the stats."
            )
            return

        api_platform = PLATFORM_MAPPING.get(platform)
        if not api_platform:
            await send_error_embed(
                interaction,
                "Invalid Platform",
                "Please use a valid platform (Xbox, Playstation, Origin)."
            )
            return

        # Fetch Apex stats from the API using asyncio.to_thread
        try:
            data = await asyncio.to_thread(fetch_apex_stats, api_platform, name)
        except PermissionError as e:
            logger.error(f"Permission Error: {e}", exc_info=True)
            await send_error_embed(
                interaction,
                "Access Denied",
                "The bot is currently unable to access the Apex Legends API. "
                "This may be due to an invalid API key or exceeding the API rate limits. "
                "Please try again later."
            )
            return

        if not data or 'data' not in data or 'segments' not in data['data']:
            await send_error_embed(
                interaction,
                "Account Not Found",
                f"No stats found for the username: **{name}** on {platform}. "
                "Please double-check your details."
            )
            return

        segments = data['data']['segments']
        if not segments:
            await send_error_embed(
                interaction,
                "No Data Available",
                f"No data found for the user: **{name}**."
            )
            return

        lifetime = segments[0]['stats']
        ranked = lifetime.get('rankScore', {})
        peak_rank = lifetime.get('lifetimePeakRankScore', {})

        # Retrieve active legend data
        active_legend_name = data['data'].get('metadata', {}).get('activeLegendName', 'Unknown')
        active_legend_data = next(
            (legend for legend in segments if legend['metadata']['name'] == active_legend_name), 
            None
        )

        # Build the embed message
        embed = build_embed(name, api_platform, active_legend_data, lifetime, ranked, peak_rank)
        await interaction.followup.send(embed=embed)

    except ValueError as e:
        logger.error(f"Validation Error: {e}", exc_info=True)
        await send_error_embed(interaction, "Validation Error", str(e))

    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)
        await send_error_embed(
            interaction,
            "Unexpected Error",
            "An unexpected error occurred. Please try again later."
        )

# Slash-command-specific error handler
@apex.error
async def apex_error_handler(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    logger.error(f"An error occurred in /apex command: {error}", exc_info=True)
    embed = discord.Embed(
        title="Command Error",
        description="An error occurred while executing the /apex command. Please try again later.",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)

# Bot-wide error event
async def on_error(event_method, *args, **kwargs):
    logger.exception(f"An error occurred in the event: {event_method}", exc_info=True)

# Function to build the embed message
def build_embed(name: str, platform: str, active_legend_data: Dict, lifetime: Dict, ranked: Dict, peak_rank: Dict) -> discord.Embed:
    legend_color = active_legend_data.get('metadata', {}).get('bgColor', '#9B8651') if active_legend_data else '#9B8651'
    embed = discord.Embed(
        title=f"Apex Legends - {name}",
        url=f"https://apex.tracker.gg/apex/profile/{platform}/{name}/overview",
        color=int(legend_color[1:], 16)
    )

    # Add lifetime stats
    embed.add_field(name="Lifetime Stats", value=format_lifetime_stats(lifetime), inline=True)

    # Add ranked stats
    embed.add_field(name="Current Rank", value=format_ranked_stats(ranked), inline=True)

    # Add peak rank
    embed.add_field(name="Peak Rank", value=format_peak_rank(peak_rank), inline=True)

    if active_legend_data and 'stats' in active_legend_data:
        embed.set_thumbnail(url=active_legend_data['metadata']['portraitImageUrl'])
        embed.add_field(
            name=f"{active_legend_data['metadata']['name']} - Currently Selected",
            value=format_active_legend_stats(active_legend_data['stats']),
            inline=False
        )

    embed.add_field(
        name="Support Us ❤️",
        value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)"
    )

    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")
    return embed

# Function to format lifetime stats
def format_lifetime_stats(lifetime: Dict) -> str:
    formatted_stats = [
        f"Level: **{format_stat_value(lifetime.get('level', {}))}**",
        f"Kills: **{format_stat_value(lifetime.get('kills', {}))}**",
        f"Damage: **{format_stat_value(lifetime.get('damage', {}))}**",
        f"Matches Played: **{format_stat_value(lifetime.get('matchesPlayed', {}))}**",
        f"Arena Winstreak: **{format_stat_value(lifetime.get('arenaWinStreak', {}))}**"
    ]
    return "\n".join(formatted_stats)

# Function to format ranked stats
def format_ranked_stats(ranked: Dict) -> str:
    rank_name = ranked.get('metadata', {}).get('rankName', 'Unranked')
    rank_value = ranked.get('value', 0)
    rank_percentile = ranked.get('percentile', 0)
    percentile_display = f"(Top {int(rank_percentile)}%)" if rank_percentile else ""
    return f"**{rank_name}**: {int(rank_value):,} {percentile_display}"

# Function to format peak rank
def format_peak_rank(peak_rank: Dict) -> str:
    peak_name = peak_rank.get('metadata', {}).get('rankName', 'Unknown')
    peak_value = peak_rank.get('value', 0)
    return f"**{peak_name}**: {int(peak_value):,}"

# Function to format active legend stats
def format_active_legend_stats(stats: Dict) -> str:
    return "\n".join(
        f"{stat_data['displayName']}: **{int(stat_data.get('value', 0))}**"
        for stat_data in stats.values()
    )

# Setup function for the bot
async def setup(client: discord.Client):
    client.tree.add_command(apex)
    client.event(on_error)

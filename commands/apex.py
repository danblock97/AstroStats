import discord
import datetime
from typing import Literal, Optional, Dict
import os
import aiohttp
import logging

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Platform Mapping Dictionary
PLATFORM_MAPPING = {
    'Xbox': 'xbl',
    'Playstation': 'psn',
    'Origin (PC)': 'origin',
}

# Helper function to retrieve Apex Legends data from the API
async def fetch_apex_stats(api_platform: str, name: str) -> Optional[Dict]:
    url = f"https://public-api.tracker.gg/v2/apex/standard/profile/{api_platform}/{name}"
    headers = {"TRN-Api-Key": os.getenv('TRN-Api-Key')}

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
                    logger.error(f"Failed to fetch stats for {name} on {api_platform}: {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Client error occurred: {e}")
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

# Helper function to send an error embed
async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=f"{description}\n\nFor more assistance, visit [AstroStats Support](https://astrostats.vercel.app)",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    await interaction.response.send_message(embed=embed)

# Main Apex Legends command
@discord.app_commands.command(name="apex", description="Check your Apex Legends Player Stats")
async def apex(interaction: discord.Interaction, platform: Literal['Xbox', 'Playstation', 'Origin (PC)'], name: str):
    try:
        # Validate input
        if not name:
            await send_error_embed(interaction, "Missing Username", "You need to provide a username for the stats.")
            return

        api_platform = PLATFORM_MAPPING.get(platform)
        if not api_platform:
            await send_error_embed(interaction, "Invalid Platform", "Please use a valid platform (Xbox, Playstation, Origin).")
            return

        # Fetch Apex stats from the API
        data = await fetch_apex_stats(api_platform, name)
        if not data or 'data' not in data or 'segments' not in data['data']:
            await send_error_embed(interaction, "Account Not Found", f"No stats found for the username: **{name}** on {platform}. Please double-check your details.")
            return
        
        segments = data['data']['segments']
        if not segments:
            await send_error_embed(interaction, "No Data Available", f"No data found for the user: **{name}**.")
            return

        lifetime = segments[0]['stats']
        ranked = lifetime.get('rankScore', {})
        peak_rank = lifetime.get('lifetimePeakRankScore', {})

        # Retrieve active legend data
        active_legend_name = data['data'].get('metadata', {}).get('activeLegendName', 'Unknown')
        active_legend_data = next(
            (legend for legend in segments if legend['metadata']['name'] == active_legend_name), None
        )

        # Build the embed message
        embed = build_embed(name, api_platform, active_legend_data, lifetime, ranked, peak_rank)
        await interaction.response.send_message(embed=embed)

    except ValueError as e:
        logger.error(f"Validation Error: {e}")
        await send_error_embed(interaction, "Validation Error", str(e))

    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        await send_error_embed(interaction, "Unexpected Error", "An unexpected error occurred. Please try again later.")

# Function to build the embed message
def build_embed(name: str, platform: str, active_legend_data: Dict, lifetime: Dict, ranked: Dict, peak_rank: Dict) -> discord.Embed:
    legend_color = active_legend_data.get('metadata', {}).get('legendColor', '#9B8651')
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
    return f"**{rank_name}**: {int(rank_value):,} (# {int(rank_percentile)}%)"

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

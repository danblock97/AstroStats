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
    try:
        if name is None:
            raise ValueError("Please provide a username.")

        if platform is None:
            raise ValueError("Please provide a platform (Xbox, Playstation, Origin).")

        api_platform = PLATFORM_MAPPING.get(platform)
        if not api_platform:
            raise ValueError("Invalid platform. Please use Xbox, Playstation, or Origin.")

        response = requests.get(f"https://public-api.tracker.gg/v2/apex/standard/profile/{api_platform}/{name}",
                                headers={"TRN-Api-Key": os.getenv('TRN-Api-Key')})

        response.raise_for_status()

        data = response.json()

        if 'data' not in data or 'segments' not in data['data']:
            error_message = f"Invalid data structure in API response. Response: {data}"
            print(f"Error: {error_message}")
            raise ValueError(error_message)

        segments = data['data']['segments']

        if not segments:
            await interaction.response.send_message(f"No segments found for the given username: {name}")
            return

        lifetime = segments[0]['stats']
        ranked = segments[0]['stats']['rankScore']
        peakRank = segments[0]['stats']['lifetimePeakRankScore']

        activeLegendName = data['data'].get('metadata', {}).get('activeLegendName', 'Unknown')
        active_legend_data = next(
            (legend for legend in segments if legend['metadata']['name'] == activeLegendName), None)

        # Helper function to get the percentile label
        def get_percentile_label(percentile):
            if percentile is not None:
                if percentile >= 90:
                    return '🌟 Top'
                else:
                    return 'Top' if percentile >= 50 else 'Bottom'
            else:
                return 'N/A'

        def format_stat_value(stat_data, stat_name):
            stat_value = stat_data.get('value')
            if stat_value is not None:
                percentile_label = get_percentile_label(stat_data.get('percentile', 0))
                percentile_value = int(stat_data.get('percentile', 0)) if percentile_label != 'N/A' else 0
                return f"{int(stat_value):,} ({percentile_label} {percentile_value}%)"
            else:
                return 'N/A'

        legend_color = active_legend_data.get('metadata', {}).get('legendColor', '#9B8651')
        # Create the embed at the beginning
        embed = discord.Embed(title=f"Apex Legends - {name}", url=f"https://apex.tracker.gg/apex/profile/{api_platform}/{name}/overview", color=int(legend_color[1:], 16))
        

        # Main lifetime stats
        level_data = lifetime.get('level', {})
        kills_data = lifetime.get('kills', {})
        damage_data = lifetime.get('damage', {})
        matches_played_data = lifetime.get('matchesPlayed', {})
        arena_winstreak_data = lifetime.get('arenaWinStreak', {})

        formatted_level = format_stat_value(level_data, "Level")
        formatted_kills = format_stat_value(kills_data, "Kills")
        formatted_damage = format_stat_value(damage_data, "Damage")
        formatted_matches_played = format_stat_value(matches_played_data, "Matches Played")
        formatted_arena_winstreak = format_stat_value(arena_winstreak_data, "Arena Winstreak")

        # Legend stats
        if active_legend_data and 'stats' in active_legend_data:
            # Embed setup
            embed.set_thumbnail(url=f"{active_legend_data['metadata']['portraitImageUrl']}")

            # Add fields to the embed only if the corresponding stats are available
            embed.add_field(name="Lifetime", value=f"Level: **{formatted_level}**"
                                                    f"\nKills: **{formatted_kills}**"
                                                    f"\nDamage: **{formatted_damage}**"
                                                    f"\nMatches Played: **{formatted_matches_played}**"
                                                    f"\nArena Winstreak: **{formatted_arena_winstreak}**", inline=True)

            # Add the dynamic fields to the embed
            embed_fields = []
            for stat_key, stat_data in active_legend_data['stats'].items():
                stat_name = stat_data.get('displayName', stat_key.capitalize())
                stat_value = int(stat_data.get('value', 0)) if stat_data.get('value') is not None else 0
                stat_percentile = stat_data.get('percentile', 0)

                field_str = f"{stat_name}: **{stat_value} ({get_percentile_label(stat_percentile)} {int(stat_percentile) if stat_percentile is not None else 0}%)**"
                embed_fields.append(field_str)

            # Add other fields to the embed
            embed.add_field(name="Current Rank",
                            value=f"**_Battle Royale Rank_**\n{ranked.get('metadata', {}).get('rankName', 0)}: **{int(ranked.get('value', 0)):,}**"
                                    f"\n# {int(ranked.get('rank', 0) or 0):,} • {int(ranked.get('percentile', 0) or 0)}%", inline=True)

            embed.add_field(name="Peak Rank",
                            value=f"**_Battle Royale Rank_**\n{peakRank.get('metadata', {}).get('rankName', 0)}: **{int(peakRank.get('value', 0)):,}**", inline=False)
            
            # Add the dynamic fields to the embed
            embed.add_field(name=f"{activeLegendName} - Currently Selected", value='\n'.join(embed_fields), inline=False)

            embed.timestamp = datetime.datetime.utcnow()
            embed.set_footer(text="Built By Goldiez ❤️")
            await interaction.response.send_message(embed=embed)

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed)

    except ValueError as e:
        print(f"Error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Oops! Something went wrong. {e}")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("Sorry, I couldn't retrieve Apex Legends stats at the moment. Please try again later.")

    except Exception as e:
        print(f"Error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("Oops! An unexpected error occurred while processing your request. Please try again later.")

def setup(client):
    client.tree.command(
        name="apex", description="Check your Apex Player Stats"
    )(Apex)

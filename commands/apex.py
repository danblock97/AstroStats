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

        if active_legend_data:
            LegendHeadshots = int(active_legend_data['stats']['headshots']['value']
                                  ) if 'headshots' in active_legend_data['stats'] and active_legend_data['stats']['headshots']['value'] != 0 else 0
            LegendDamage = int(active_legend_data['stats']['damage']['value']
                               ) if 'damage' in active_legend_data['stats'] and active_legend_data['stats']['damage']['value'] != 0 else 0
            LegendKills = int(active_legend_data['stats']['kills']['value']
                              ) if 'kills' in active_legend_data['stats'] and active_legend_data['stats']['kills']['value'] != 0 else 0
        else:
            LegendHeadshots = LegendDamage = LegendKills = 0

        def get_percentile_label(percentile):
            if percentile is not None:
                if percentile >= 90:
                    return '🌟 Top'
                else:
                    return 'Top' if percentile >= 50 else 'Bottom'
            else:
                return 0

        legend_color = active_legend_data.get('metadata', {}).get('legendColor', '#9B8651')
        embed = discord.Embed(color=int(legend_color[1:], 16))
        embed.set_author(name=f"Apex Legends - {name}", url=f"https://apex.tracker.gg/apex/profile/{api_platform}/{name}/overview")

        embed.set_thumbnail(url=f"{active_legend_data['metadata']['portraitImageUrl']}")

        embed.add_field(name="Lifetime", value=f"Level: **{int(lifetime.get('level', {}).get('value', 0)):,}** ({get_percentile_label(lifetime.get('level', {}).get('percentile', 0))} {int(lifetime.get('level', {}).get('percentile', 0))}%)"
                        f"\nKills: **{int(lifetime.get('kills', {}).get('value', 0)):,}** ({get_percentile_label(lifetime.get('kills', {}).get('percentile', 0))} {int(lifetime.get('kills', {}).get('percentile', 0))}%)"
                        f"\nDamage: **{int(lifetime.get('damage', {}).get('value', 0)):,}** ({get_percentile_label(lifetime.get('damage', {}).get('percentile', 0))} {int(lifetime.get('damage', {}).get('percentile', 0))}%)"
                        f"\nMatches Played: **{int(lifetime.get('matchesPlayed', {}).get('value', 0)):,}**"
                        f"\nArena Winstreak: **{int(lifetime.get('arenaWinStreak', {}).get('value', 0)):,}**", inline=True)

        embed.add_field(name=f"{activeLegendName} - Currently Selected",
                        value=f"Headshots: **{LegendHeadshots:,}** ({get_percentile_label(active_legend_data.get('stats', {}).get('kills', {}).get('percentile', 0))} {int(active_legend_data.get('stats', {}).get('kills', {}).get('percentile', 0))}%)"
                        f"\nDamage: **{LegendDamage:,}** ({get_percentile_label(active_legend_data.get('stats', {}).get('damage', {}).get('percentile', 0))} {int(active_legend_data.get('stats', {}).get('damage', {}).get('percentile', 0))}%)"
                        f"\nKills: **{LegendKills:,}** ({get_percentile_label(active_legend_data.get('stats', {}).get('headshots', {}).get('percentile', 0))} {int(active_legend_data.get('stats', {}).get('headshots', {}).get('percentile', 0))}%)", inline=True)

        embed.add_field(name="Current Rank",
                        value=f"**_Battle Royale Rank_**\n{ranked.get('metadata', {}).get('rankName', 0)}: **{int(ranked.get('value', 0)):,}**"
                        f"\n# {int(ranked.get('rank', 0)):,} • {int(ranked.get('percentile', 0))}%", inline=False)

        embed.add_field(name="Peak Rank",
                        value=f"**_Battle Royale Rank_**\n{peakRank.get('metadata', {}).get('rankName', 0)}: **{int(ranked.get('value', 0)):,}**", inline=True)
        

        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="Join our Discord Server for support. | Built By Goldiez ❤️")
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
    client.tree.command(name="apex", description="Lists all available commands")(Apex)

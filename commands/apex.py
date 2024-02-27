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

    try:
        data = response.json()

        if 'data' not in data or 'segments' not in data['data']:
            print(
                f"Error: Invalid data structure in API response. Response: {data}")
            await interaction.response.send_message('Failed to retrieve Apex stats. The Apex API is Currently Unavailable')
            return

        segments = data['data']['segments']

        if not segments:
            await interaction.response.send_message(f"No segments found for the given username: {name}")
            return

        lifetime = segments[0]['stats']
        ranked = segments[0]['stats']['rankScore']
        peakRank = segments[0]['stats']['lifetimePeakRankScore']

        activeLegendName = data['data'].get(
            'metadata', {}).get('activeLegendName', 'Unknown')

        # Find the legend in segments data whose name matches activeLegendName
        active_legend_data = next(
            (legend for legend in segments if legend['metadata']['name'] == activeLegendName), None)

        if active_legend_data:
            # Extract specific legend stats and cast to integers
            LegendHeadshots = int(active_legend_data['stats']['headshots']['value']
                                  ) if 'headshots' in active_legend_data['stats'] and active_legend_data['stats']['headshots']['value'] != 0 else 0
            LegendDamage = int(active_legend_data['stats']['damage']['value']
                               ) if 'damage' in active_legend_data['stats'] and active_legend_data['stats']['damage']['value'] != 0 else 0
            LegendKills = int(active_legend_data['stats']['kills']['value']
                              ) if 'kills' in active_legend_data['stats'] and active_legend_data['stats']['kills']['value'] != 0 else 0

        else:
            # If no matching legend is found, set stats to N/A
            LegendHeadshots = LegendDamage = LegendKills = 0

        # Function to determine if the percentile is in the top or bottom
        def get_percentile_label(percentile):
            if percentile is not None:
                if percentile >= 90:
                    return '🌟 Top'
                else:
                    return 'Top' if percentile >= 50 else 'Bottom'
            else:
                return 0

        embed = discord.Embed(color=0xdd4f7a)
        embed.set_author(name=f"Apex Legends - {name}", url=f"https://apex.tracker.gg/apex/profile/{api_platform}/{name}/overview")

        embed.set_thumbnail(url=f"{ranked['metadata']['iconUrl']}")

        embed.add_field(name="Lifetime", value=f"Level: **{int(lifetime.get('level', {}).get('value', 0)):,}** ({get_percentile_label(lifetime.get('level', {}).get('percentile', 0))} {int(lifetime.get('level', {}).get('percentile', 0))}%)"
                        f"\nKills: **{int(lifetime.get('kills', {}).get('value', 0)):,}** ({get_percentile_label(lifetime.get(
                            'kills', {}).get('percentile', 0))} {int(lifetime.get('kills', {}).get('percentile', 0))}%)"
                        f"\nDamage: **{int(lifetime.get('damage', {}).get('value', 0)):,}** ({get_percentile_label(lifetime.get(
                            'damage', {}).get('percentile', 0))} {int(lifetime.get('damage', {}).get('percentile', 0))}%)"
                        f"\nMatches Played: **{
                            int(lifetime.get('matchesPlayed', {}).get('value', 0)):,}**"
                        f"\nArena Winstreak: **{int(lifetime.get('arenaWinStreak', {}).get('value', 0)):,}**", inline=True)

        embed.add_field(name=f"{activeLegendName} - Currently Selected",
                        value=f"Headshots: **{LegendHeadshots:,}** ({get_percentile_label(active_legend_data.get('stats', {}).get(
                            'kills', {}).get('percentile', 0))} {int(active_legend_data.get('stats', {}).get('kills', {}).get('percentile', 0))}%)"
                        f"\nDamage: **{LegendDamage:,}** ({get_percentile_label(active_legend_data.get('stats', {}).get('damage', {}).get(
                            'percentile', 0))} {int(active_legend_data.get('stats', {}).get('damage', {}).get('percentile', 0))}%)"
                        f"\nKills: **{LegendKills:,}** ({get_percentile_label(active_legend_data.get('stats', {}).get('headshots', {}).get('percentile', 0))} {int(active_legend_data.get('stats', {}).get('headshots', {}).get('percentile', 0))}%)", inline=True)

        embed.add_field(name="Current Rank",
                        value=f"**_Battle Royale Rank_**\n{ranked.get('metadata', {}).get(
                            'rankName', 0)}: **{int(ranked.get('value', 0)):,}**"
                        f"\n# {int(ranked.get('rank', 0)):,} • {int(ranked.get('percentile', 0))}%", inline=False)

        embed.add_field(name="Peak Rank",
                        value=f"**_Battle Royale Rank_**\n{peakRank.get('metadata', {}).get(
                            'rankName', 0)}: **{int(ranked.get('value', 0)):,}**", inline=True)

        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await interaction.response.send_message(embed=embed)

    except KeyError as e:
        await interaction.response.send_message(f"Failed to retrieve Apex Legends stats. Key error: {e}")
    except (ValueError, requests.exceptions.RequestException) as e:
        await interaction.response.send_message(f"Failed to retrieve Apex Legends stats. Error: {e}")


def setup(client):
    client.tree.command(
        name="apex", description="Lists all available commands")(Apex)

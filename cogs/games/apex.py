import datetime
import logging
import asyncio
from typing import Literal, Dict

import discord
from discord import app_commands
from discord.ext import commands

from config.constants import APEX_PLATFORM_MAPPING
from core.errors import send_error_embed
from services.api.apex import fetch_apex_stats, format_stat_value
from core.utils import get_conditional_embed

logger = logging.getLogger(__name__)


class ApexCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="apex", description="Check your Apex Legends Player Stats")
    async def apex(
            self,
            interaction: discord.Interaction,
            platform: Literal['Xbox', 'Playstation', 'Origin (PC)'],
            name: str
    ):
        try:
            await interaction.response.defer()

            if not name:
                await send_error_embed(
                    interaction,
                    "Missing Username",
                    "You need to provide a username for the stats."
                )
                return

            try:
                data = await asyncio.to_thread(fetch_apex_stats, platform, name)
            except Exception as e:
                logger.error(f"API Error: {e}", exc_info=True)
                await send_error_embed(
                    interaction,
                    "API Error",
                    "There was an error retrieving Apex Legends stats. Please try again later."
                )
                return

            if not data or 'data' not in data or 'segments' not in data['data']:
                await send_error_embed(
                    interaction,
                    "Account Not Found",
                    f"No stats found for the username: **{name}** on {platform}. "
                    "Please double-check your details are up to date on [Apex Tracker](https://apex.tracker.gg)."
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

            active_legend_name = data['data'].get('metadata', {}).get('activeLegendName', 'Unknown')
            active_legend_data = next(
                (legend for legend in segments if legend['metadata']['name'] == active_legend_name),
                None
            )

            embed = self.build_embed(name, platform, active_legend_data, lifetime, ranked, peak_rank)

            conditional_embed = await get_conditional_embed(interaction, 'APEX_EMBED', discord.Color.orange())
            embeds = [embed]
            if conditional_embed:
                embeds.append(conditional_embed)

            await interaction.followup.send(embeds=embeds)

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

    def build_embed(
            self,
            name: str,
            platform: str,
            active_legend_data: Dict,
            lifetime: Dict,
            ranked: Dict,
            peak_rank: Dict
    ) -> discord.Embed:
        api_platform = APEX_PLATFORM_MAPPING.get(platform, '')
        legend_color = '#9B8651'
        if active_legend_data:
            legend_color = active_legend_data.get('metadata', {}).get('bgColor', '#9B8651')

        embed = discord.Embed(
            title=f"Apex Legends - {name}",
            url=f"https://apex.tracker.gg/apex/profile/{api_platform}/{name}/overview",
            color=int(legend_color.lstrip('#'), 16),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        embed.add_field(
            name="Lifetime Stats",
            value=self.format_lifetime_stats(lifetime),
            inline=True
        )
        embed.add_field(
            name="Current Rank",
            value=self.format_ranked_stats(ranked),
            inline=True
        )
        embed.add_field(
            name="Peak Rank",
            value=self.format_peak_rank(peak_rank),
            inline=True
        )

        if active_legend_data and 'stats' in active_legend_data:
            embed.set_thumbnail(url=active_legend_data['metadata']['portraitImageUrl'])
            embed.add_field(
                name=f"{active_legend_data['metadata']['name']} - Currently Selected",
                value=self.format_active_legend_stats(active_legend_data['stats']),
                inline=False
            )

        embed.add_field(
            name="Support Us ❤️",
            value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)",
            inline=False
        )
        embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")
        return embed

    def format_lifetime_stats(self, lifetime: Dict) -> str:
        formatted_stats = [
            f"Level: **{format_stat_value(lifetime.get('level', {}))}**",
            f"Kills: **{format_stat_value(lifetime.get('kills', {}))}**",
            f"Damage: **{format_stat_value(lifetime.get('damage', {}))}**",
            f"Matches Played: **{format_stat_value(lifetime.get('matchesPlayed', {}))}**",
            f"Arena Winstreak: **{format_stat_value(lifetime.get('arenaWinStreak', {}))}**"
        ]
        return "\n".join(formatted_stats)

    def format_ranked_stats(self, ranked: Dict) -> str:
        rank_name = ranked.get('metadata', {}).get('rankName', 'Unranked')
        rank_value = ranked.get('value', 0)
        rank_percentile = ranked.get('percentile', 0)
        percentile_display = f"(Top {int(rank_percentile)}%)" if rank_percentile else ""
        return f"**{rank_name}**: {int(rank_value):,} {percentile_display}"

    def format_peak_rank(self, peak_rank: Dict) -> str:
        peak_name = peak_rank.get('metadata', {}).get('rankName', 'Unknown')
        peak_value = peak_rank.get('value', 0)
        return f"**{peak_name}**: {int(peak_value):,}"

    def format_active_legend_stats(self, stats: Dict) -> str:
        return "\n".join(
            f"{stat_data['displayName']}: **{int(stat_data.get('value', 0))}**"
            for stat_data in stats.values()
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ApexCog(bot))
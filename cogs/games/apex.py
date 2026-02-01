import datetime
import logging
import asyncio
import os
from typing import Literal, Dict

import discord
from discord import app_commands
from discord.ext import commands

from config.constants import APEX_PLATFORM_MAPPING
from core.errors import send_error_embed, ResourceNotFoundError, APIError
from services.api.apex import fetch_apex_stats, format_stat_value
from services.compare_image import compare_image_generator, compare_values
from core.utils import get_conditional_embed
from ui.embeds import get_premium_promotion_view

logger = logging.getLogger(__name__)


class ApexCog(commands.GroupCog, group_name="apex"):
    """A cog grouping Apex Legends commands under `/apex`."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        # Get the absolute path to the images
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    async def _fetch_player_data(self, platform: str, name: str):
        """Fetch and parse Apex stats for a player. Returns (segments, lifetime, ranked, peak_rank, active_legend_data, data) or raises."""
        data = await asyncio.to_thread(fetch_apex_stats, platform, name)

        if not data or 'data' not in data or 'segments' not in data['data']:
            return None

        segments = data['data']['segments']
        if not segments:
            return None

        lifetime = segments[0]['stats']
        ranked = lifetime.get('rankScore', {})
        peak_rank = lifetime.get('lifetimePeakRankScore', {})

        active_legend_name = data['data'].get('metadata', {}).get('activeLegendName', 'Unknown')
        active_legend_data = next(
            (legend for legend in segments if legend['metadata']['name'] == active_legend_name),
            None
        )

        return {
            'segments': segments,
            'lifetime': lifetime,
            'ranked': ranked,
            'peak_rank': peak_rank,
            'active_legend_data': active_legend_data,
            'data': data
        }

    @app_commands.command(name="stats", description="Check your Apex Legends Player Stats")
    async def stats(
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
                    "You need to provide a username for the stats.",
                    notify_logged=False
                )
                return

            try:
                player = await self._fetch_player_data(platform, name)
            except ResourceNotFoundError as e:
                logger.warning(f"Resource Not Found: {e}", exc_info=True)
                await send_error_embed(
                    interaction,
                    "Account Not Found",
                    f"No stats found for the username: **{name}** on **{platform}**. "
                    "Please ensure the username and platform are correct and the profile exists on [Apex Tracker](https://apex.tracker.gg).",
                    notify_logged=False
                )
                return
            except APIError as e:
                logger.error(f"API Error: {e}", exc_info=True)
                await send_error_embed(
                    interaction,
                    "API Error",
                    str(e)
                )
                return
            except Exception as e:
                logger.error(f"Unexpected API Error: {e}", exc_info=True)
                await send_error_embed(
                    interaction,
                    "API Error",
                    "There was an error retrieving Apex Legends stats. Please try again later."
                )
                return

            if not player:
                await send_error_embed(
                    interaction,
                    "Account Not Found",
                    f"No stats found for the username: **{name}** on {platform}. "
                    "Please double-check your details are up to date on [Apex Tracker](https://apex.tracker.gg).",
                    notify_logged=False
                )
                return

            embed = self.build_embed(name, platform, player['active_legend_data'], player['lifetime'], player['ranked'], player['peak_rank'])

            conditional_embed = await get_conditional_embed(interaction, 'APEX_EMBED', discord.Color.orange())
            embeds = [embed]
            if conditional_embed:
                embeds.append(conditional_embed)

            premium_view = get_premium_promotion_view(str(interaction.user.id))

            await interaction.followup.send(
                embeds=embeds,
                view=premium_view,
                files=[discord.File(self.astrostats_img, "astrostats.png")]
            )

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

    @app_commands.command(name="compare", description="Compare two Apex Legends players side-by-side")
    async def compare(
            self,
            interaction: discord.Interaction,
            platform1: Literal['Xbox', 'Playstation', 'Origin (PC)'],
            name1: str,
            platform2: Literal['Xbox', 'Playstation', 'Origin (PC)'],
            name2: str
    ):
        try:
            await interaction.response.defer()

            errors = []
            player1, player2 = None, None

            try:
                player1 = await self._fetch_player_data(platform1, name1)
            except ResourceNotFoundError:
                errors.append(f"No stats found for **{name1}** on **{platform1}**.")
            except (APIError, Exception) as e:
                errors.append(f"Error fetching stats for **{name1}**: {e}")

            try:
                player2 = await self._fetch_player_data(platform2, name2)
            except ResourceNotFoundError:
                errors.append(f"No stats found for **{name2}** on **{platform2}**.")
            except (APIError, Exception) as e:
                errors.append(f"Error fetching stats for **{name2}**: {e}")

            if errors:
                await send_error_embed(
                    interaction,
                    "Player Lookup Failed",
                    "\n".join(errors),
                    notify_logged=False
                )
                return

            if not player1 or not player2:
                await send_error_embed(
                    interaction,
                    "No Data Available",
                    "Could not retrieve stats for one or both players.",
                    notify_logged=False
                )
                return

            rows = self._build_compare_rows(player1, player2)
            img_buf = compare_image_generator.create_image(
                title="Apex Legends Comparison",
                player1_name=f"{name1} ({platform1})",
                player2_name=f"{name2} ({platform2})",
                rows=rows,
                accent_color=(155, 134, 81),
            )

            if img_buf:
                await interaction.followup.send(
                    file=discord.File(img_buf, "apex_compare.png")
                )
            else:
                await send_error_embed(interaction, "Image Error", "Failed to generate comparison image.")

        except Exception as e:
            logger.error(f"Unexpected Error in compare: {e}", exc_info=True)
            await send_error_embed(
                interaction,
                "Unexpected Error",
                "An unexpected error occurred. Please try again later."
            )

    def _build_compare_rows(self, p1: Dict, p2: Dict):
        """Build comparison rows for the image generator."""
        lt1, lt2 = p1['lifetime'], p2['lifetime']
        rows = []

        stat_keys = [
            ("Level", "level"),
            ("Kills", "kills"),
            ("Damage", "damage"),
            ("Matches Played", "matchesPlayed"),
        ]
        for label, key in stat_keys:
            v1 = lt1.get(key, {}).get('value')
            v2 = lt2.get(key, {}).get('value')
            s1 = f"{int(v1):,}" if v1 is not None else "N/A"
            s2 = f"{int(v2):,}" if v2 is not None else "N/A"
            s1, s2 = compare_values(v1, v2, s1, s2)
            rows.append((label, s1, s2))

        # Rank
        r1 = p1['ranked']
        r2 = p2['ranked']
        r1_name = r1.get('metadata', {}).get('rankName', 'Unranked')
        r1_val = r1.get('value', 0)
        r2_name = r2.get('metadata', {}).get('rankName', 'Unranked')
        r2_val = r2.get('value', 0)
        rs1 = f"{r1_name} ({int(r1_val):,} RP)"
        rs2 = f"{r2_name} ({int(r2_val):,} RP)"
        rs1, rs2 = compare_values(r1_val, r2_val, rs1, rs2)
        rows.append(("Current Rank", rs1, rs2))

        # Peak rank
        pk1 = p1['peak_rank']
        pk2 = p2['peak_rank']
        pk1_name = pk1.get('metadata', {}).get('rankName', 'Unknown')
        pk1_val = pk1.get('value', 0)
        pk2_name = pk2.get('metadata', {}).get('rankName', 'Unknown')
        pk2_val = pk2.get('value', 0)
        pks1 = f"{pk1_name} ({int(pk1_val):,})"
        pks2 = f"{pk2_name} ({int(pk2_val):,})"
        pks1, pks2 = compare_values(pk1_val, pk2_val, pks1, pks2)
        rows.append(("Peak Rank", pks1, pks2))

        # Active legend
        l1 = p1.get('active_legend_data')
        l2 = p2.get('active_legend_data')
        l1_name = l1['metadata']['name'] if l1 else "None"
        l2_name = l2['metadata']['name'] if l2 else "None"
        rows.append(("Active Legend", l1_name, l2_name))

        return rows

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

        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")
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
        rank_percentile = ranked.get('percentile')
        
        # Use shared helper for consistency
        from services.api.apex import get_formatted_percentile
        percentile_display = ""
        if rank_percentile is not None:
             p_str = get_formatted_percentile(rank_percentile)
             if p_str != 'N/A':
                 percentile_display = f"({p_str})"

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

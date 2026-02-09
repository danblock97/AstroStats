import asyncio
import datetime
import logging
import os
from typing import Any, Dict, Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from config.constants import APEX_PLATFORM_MAPPING
from core.errors import APIError, ResourceNotFoundError, send_error_embed
from core.utils import get_conditional_embed
from services.api.apex import fetch_apex_stats, format_stat_value
from ui.embeds import get_premium_promotion_view

logger = logging.getLogger(__name__)


class ApexCog(commands.GroupCog, group_name="apex"):
    """A cog grouping Apex commands under `/apex`."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, "images", "astrostats.png")

    async def _fetch_player_data(self, platform: str, name: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse Apex stats for a player."""
        data = await asyncio.to_thread(fetch_apex_stats, platform, name)
        if not data or "data" not in data or "segments" not in data["data"]:
            return None

        segments = data["data"]["segments"]
        if not segments:
            return None

        lifetime = segments[0].get("stats", {})
        ranked = lifetime.get("rankScore", {})
        peak_rank = lifetime.get("lifetimePeakRankScore", {})

        active_legend_name = data["data"].get("metadata", {}).get("activeLegendName", "Unknown")
        active_legend_data = next(
            (legend for legend in segments if legend.get("metadata", {}).get("name") == active_legend_name),
            None,
        )

        return {
            "segments": segments,
            "lifetime": lifetime,
            "ranked": ranked,
            "peak_rank": peak_rank,
            "active_legend_data": active_legend_data,
            "data": data,
        }

    @app_commands.command(name="stats", description="Check Apex Legends player stats")
    async def stats(
        self,
        interaction: discord.Interaction,
        platform: Literal["Xbox", "Playstation", "Origin (PC)"],
        name: str,
    ):
        try:
            await interaction.response.defer()

            if not name:
                await send_error_embed(
                    interaction,
                    "Missing Username",
                    "You need to provide a username for the stats.",
                    notify_logged=False,
                )
                return

            try:
                player = await self._fetch_player_data(platform, name)
            except ResourceNotFoundError as e:
                logger.warning("Resource Not Found: %s", e, exc_info=True)
                await send_error_embed(
                    interaction,
                    "Account Not Found",
                    f"No stats found for the username: **{name}** on **{platform}**. "
                    "Please ensure the username and platform are correct and the profile exists on [Apex Tracker](https://apex.tracker.gg).",
                    notify_logged=False,
                )
                return
            except APIError as e:
                logger.error("API Error: %s", e, exc_info=True)
                await send_error_embed(interaction, "API Error", str(e))
                return
            except Exception as e:
                logger.error("Unexpected API Error: %s", e, exc_info=True)
                await send_error_embed(
                    interaction,
                    "API Error",
                    "There was an error retrieving Apex Legends stats. Please try again later.",
                )
                return

            if not player:
                await send_error_embed(
                    interaction,
                    "Account Not Found",
                    f"No stats found for the username: **{name}** on **{platform}**. "
                    "Please double-check your details are up to date on [Apex Tracker](https://apex.tracker.gg).",
                    notify_logged=False,
                )
                return

            embed = self.build_embed(
                name,
                platform,
                player["active_legend_data"],
                player["lifetime"],
                player["ranked"],
                player["peak_rank"],
            )

            conditional_embed = await get_conditional_embed(interaction, "APEX_EMBED", discord.Color.orange())
            embeds = [embed]
            if conditional_embed:
                embeds.append(conditional_embed)

            premium_view = get_premium_promotion_view(str(interaction.user.id))

            await interaction.followup.send(
                embeds=embeds,
                view=premium_view,
                files=[discord.File(self.astrostats_img, "astrostats.png")],
            )

        except ValueError as e:
            logger.error("Validation Error: %s", e, exc_info=True)
            await send_error_embed(interaction, "Validation Error", str(e))
        except Exception as e:
            logger.error("Unexpected Error: %s", e, exc_info=True)
            await send_error_embed(
                interaction,
                "Unexpected Error",
                "An unexpected error occurred. Please try again later.",
            )

    @app_commands.command(name="compare", description="Compare two Apex Legends players")
    @app_commands.describe(
        platform1="Platform for player 1",
        name1="Username for player 1",
        platform2="Platform for player 2",
        name2="Username for player 2",
    )
    async def compare(
        self,
        interaction: discord.Interaction,
        platform1: Literal["Xbox", "Playstation", "Origin (PC)"],
        name1: str,
        platform2: Literal["Xbox", "Playstation", "Origin (PC)"],
        name2: str,
    ):
        await interaction.response.defer()

        if not name1 or not name2:
            await send_error_embed(
                interaction,
                "Missing Username",
                "Please provide usernames for both players.",
                notify_logged=False,
            )
            return

        try:
            results = await asyncio.gather(
                self._fetch_player_data(platform1, name1),
                self._fetch_player_data(platform2, name2),
                return_exceptions=True,
            )
        except Exception as e:
            logger.error("Apex compare request failure: %s", e, exc_info=True)
            await send_error_embed(interaction, "API Error", "Failed to fetch Apex stats. Please try again later.")
            return

        errors = []
        players: list[Optional[Dict[str, Any]]] = [None, None]

        for idx, result in enumerate(results):
            player_name = name1 if idx == 0 else name2
            player_platform = platform1 if idx == 0 else platform2

            if isinstance(result, ResourceNotFoundError):
                errors.append(f"No stats found for **{player_name}** on **{player_platform}**.")
                continue
            if isinstance(result, APIError):
                await send_error_embed(interaction, "API Error", str(result))
                return
            if isinstance(result, Exception):
                logger.error("Unexpected compare fetch error: %s", result, exc_info=True)
                await send_error_embed(interaction, "API Error", "Failed to fetch Apex stats. Please try again later.")
                return
            if not result:
                errors.append(f"No stats found for **{player_name}** on **{player_platform}**.")
                continue

            players[idx] = result

        if errors:
            await send_error_embed(interaction, "Account Not Found", "\n".join(errors), notify_logged=False)
            return

        embed = self.build_compare_embed(
            name1=name1,
            platform1=platform1,
            player1=players[0],
            name2=name2,
            platform2=platform2,
            player2=players[1],
        )
        await interaction.followup.send(
            embed=embed,
            files=[discord.File(self.astrostats_img, "astrostats.png")],
        )

    def build_embed(
        self,
        name: str,
        platform: str,
        active_legend_data: Optional[Dict[str, Any]],
        lifetime: Dict[str, Any],
        ranked: Dict[str, Any],
        peak_rank: Dict[str, Any],
    ) -> discord.Embed:
        api_platform = APEX_PLATFORM_MAPPING.get(platform, "")
        legend_color = "#9B8651"
        if active_legend_data:
            legend_color = active_legend_data.get("metadata", {}).get("bgColor", "#9B8651")

        embed = discord.Embed(
            title=f"Apex Legends - {name}",
            url=f"https://apex.tracker.gg/apex/profile/{api_platform}/{name}/overview",
            color=int(legend_color.lstrip("#"), 16),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        embed.add_field(name="Lifetime Stats", value=self.format_lifetime_stats(lifetime), inline=True)
        embed.add_field(name="Current Rank", value=self.format_ranked_stats(ranked), inline=True)
        embed.add_field(name="Peak Rank", value=self.format_peak_rank(peak_rank), inline=True)

        if active_legend_data and "stats" in active_legend_data:
            embed.set_thumbnail(url=active_legend_data["metadata"]["portraitImageUrl"])
            embed.add_field(
                name=f"{active_legend_data['metadata']['name']} - Currently Selected",
                value=self.format_active_legend_stats(active_legend_data["stats"]),
                inline=False,
            )

        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")
        return embed

    def build_compare_embed(
        self,
        name1: str,
        platform1: str,
        player1: Optional[Dict[str, Any]],
        name2: str,
        platform2: str,
        player2: Optional[Dict[str, Any]],
    ) -> discord.Embed:
        p1 = player1 or {}
        p2 = player2 or {}

        p1_lifetime = p1.get("lifetime", {})
        p2_lifetime = p2.get("lifetime", {})
        p1_ranked = p1.get("ranked", {})
        p2_ranked = p2.get("ranked", {})
        p1_peak = p1.get("peak_rank", {})
        p2_peak = p2.get("peak_rank", {})

        level1 = self._stat_numeric(p1_lifetime.get("level", {}))
        level2 = self._stat_numeric(p2_lifetime.get("level", {}))
        kills1 = self._stat_numeric(p1_lifetime.get("kills", {}))
        kills2 = self._stat_numeric(p2_lifetime.get("kills", {}))
        damage1 = self._stat_numeric(p1_lifetime.get("damage", {}))
        damage2 = self._stat_numeric(p2_lifetime.get("damage", {}))
        matches1 = self._stat_numeric(p1_lifetime.get("matchesPlayed", {}))
        matches2 = self._stat_numeric(p2_lifetime.get("matchesPlayed", {}))
        streak1 = self._stat_numeric(p1_lifetime.get("arenaWinStreak", {}))
        streak2 = self._stat_numeric(p2_lifetime.get("arenaWinStreak", {}))
        rank_points1 = self._to_float(p1_ranked.get("value"))
        rank_points2 = self._to_float(p2_ranked.get("value"))
        peak_points1 = self._to_float(p1_peak.get("value"))
        peak_points2 = self._to_float(p2_peak.get("value"))

        rank_name1 = p1_ranked.get("metadata", {}).get("rankName", "Unranked")
        rank_name2 = p2_ranked.get("metadata", {}).get("rankName", "Unranked")
        peak_name1 = p1_peak.get("metadata", {}).get("rankName", "Unknown")
        peak_name2 = p2_peak.get("metadata", {}).get("rankName", "Unknown")

        p1_lines = [
            f"Platform: **{platform1}**",
            f"Current Rank: **{rank_name1}**",
            f"Peak Rank: **{peak_name1}**",
        ]
        p2_lines = [
            f"Platform: **{platform2}**",
            f"Current Rank: **{rank_name2}**",
            f"Peak Rank: **{peak_name2}**",
        ]

        compare_rows = [
            ("Level", level1, level2, self._format_number(level1), self._format_number(level2), True),
            ("Kills", kills1, kills2, self._format_number(kills1), self._format_number(kills2), True),
            ("Damage", damage1, damage2, self._format_number(damage1), self._format_number(damage2), True),
            ("Matches Played", matches1, matches2, self._format_number(matches1), self._format_number(matches2), True),
            ("Arena Win Streak", streak1, streak2, self._format_number(streak1), self._format_number(streak2), True),
            ("Rank Points", rank_points1, rank_points2, self._format_number(rank_points1), self._format_number(rank_points2), True),
            ("Peak Rank Points", peak_points1, peak_points2, self._format_number(peak_points1), self._format_number(peak_points2), True),
        ]

        for label, val1, val2, disp1, disp2, higher_is_better in compare_rows:
            p1_lines.append(f"{label}: **{disp1}**")
            p2_lines.append(f"{label}: **{disp2}**")

        embed = discord.Embed(
            title="Apex Legends Compare",
            description=f"**{name1}** vs **{name2}**",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name=f"Player 1: {name1}", value="\n".join(p1_lines), inline=False)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)
        embed.add_field(name=f"Player 2: {name2}", value="\n".join(p2_lines), inline=False)
        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")
        return embed

    @staticmethod
    def _stat_numeric(stat_data: Dict[str, Any]) -> Optional[float]:
        if not isinstance(stat_data, dict):
            return None
        return ApexCog._to_float(stat_data.get("value"))

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    @staticmethod
    def _format_number(value: Optional[float]) -> str:
        if value is None:
            return "N/A"
        if float(value).is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"

    def format_lifetime_stats(self, lifetime: Dict[str, Any]) -> str:
        formatted_stats = [
            f"Level: **{format_stat_value(lifetime.get('level', {}))}**",
            f"Kills: **{format_stat_value(lifetime.get('kills', {}))}**",
            f"Damage: **{format_stat_value(lifetime.get('damage', {}))}**",
            f"Matches Played: **{format_stat_value(lifetime.get('matchesPlayed', {}))}**",
            f"Arena Winstreak: **{format_stat_value(lifetime.get('arenaWinStreak', {}))}**",
        ]
        return "\n".join(formatted_stats)

    def format_ranked_stats(self, ranked: Dict[str, Any]) -> str:
        rank_name = ranked.get("metadata", {}).get("rankName", "Unranked")
        rank_value = ranked.get("value", 0)
        rank_percentile = ranked.get("percentile")

        from services.api.apex import get_formatted_percentile

        percentile_display = ""
        if rank_percentile is not None:
            p_str = get_formatted_percentile(rank_percentile)
            if p_str != "N/A":
                percentile_display = f"({p_str})"

        return f"**{rank_name}**: {int(rank_value):,} {percentile_display}".rstrip()

    def format_peak_rank(self, peak_rank: Dict[str, Any]) -> str:
        peak_name = peak_rank.get("metadata", {}).get("rankName", "Unknown")
        peak_value = peak_rank.get("value", 0)
        return f"**{peak_name}**: {int(peak_value):,}"

    def format_active_legend_stats(self, stats: Dict[str, Any]) -> str:
        return "\n".join(
            f"{stat_data['displayName']}: **{int(stat_data.get('value', 0))}**"
            for stat_data in stats.values()
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ApexCog(bot))

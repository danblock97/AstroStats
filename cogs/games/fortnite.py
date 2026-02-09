import asyncio
import datetime
import logging
import os
import urllib.parse
from typing import Any, Dict, Literal, Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from config.constants import FORTNITE_TIME_MAPPING
from config.settings import FORTNITE_API_KEY
from core.errors import send_error_embed
from core.utils import get_conditional_embed
from ui.embeds import get_premium_promotion_view

logger = logging.getLogger(__name__)


class FortniteCog(commands.GroupCog, group_name="fortnite"):
    """A cog grouping Fortnite commands under `/fortnite`."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, "images", "astrostats.png")
        self.fortnite_thumbnail = os.path.join(self.base_path, "images", "fortnite_thumbnail.png")

    async def fetch_fortnite_stats(self, name: str, time_window: str) -> Optional[Dict[str, Any]]:
        if not FORTNITE_API_KEY:
            logger.error("Fortnite API key not found. Please check your .env file.")
            return None

        url = f"https://fortnite-api.com/v2/stats/br/v2?timeWindow={time_window}&name={name}"
        headers = {"Authorization": FORTNITE_API_KEY}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    status = response.status
                    if status == 200:
                        return await response.json()
                    if status == 404:
                        return None

                    logger.error("Failed to fetch stats for %s. HTTP %s received.", name, status)
                    return None
            except aiohttp.ClientError as e:
                logger.error("Client error occurred while fetching Fortnite stats: %s", e, exc_info=True)
                return None

    async def _fetch_player_stats(self, name: str, time_window: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse Fortnite stats for a player."""
        data = await self.fetch_fortnite_stats(name, time_window)
        if not data or "data" not in data:
            return None

        stats = data["data"]
        account = stats.get("account", {})
        battle_pass = stats.get("battlePass", {})
        overall_stats = stats.get("stats", {}).get("all", {}).get("overall", {})

        wins = overall_stats.get("wins", 0)
        matches = overall_stats.get("matches", 0)
        calculated_win_rate = wins / matches if matches > 0 else 0

        return {
            "stats": stats,
            "account": account,
            "battle_pass": battle_pass,
            "overall": overall_stats,
            "wins": wins,
            "matches": matches,
            "win_rate": calculated_win_rate,
        }

    @app_commands.command(name="stats", description="Check Fortnite player stats")
    async def stats(
        self,
        interaction: discord.Interaction,
        time: Literal["Season", "Lifetime"],
        name: str,
    ):
        try:
            await interaction.response.defer()

            time_window = FORTNITE_TIME_MAPPING.get(time)
            if not time_window:
                await send_error_embed(
                    interaction,
                    "Invalid Time Window",
                    "Please choose a valid time window (Season or Lifetime).",
                )
                return

            player = await self._fetch_player_stats(name, time_window)
            if not player:
                await send_error_embed(
                    interaction,
                    "Account Not Found",
                    (
                        f"No stats found for **{name}** for the selected period. "
                        "Epic may not have updated your stats yet. Please double-check your details and try again."
                    ),
                )
                return

            embed = self.build_embed(name, player["account"], player["battle_pass"], player["stats"], player["win_rate"])

            conditional_embed = await get_conditional_embed(interaction, "FORTNITE_EMBED", discord.Color.orange())
            embeds = [embed]
            if conditional_embed:
                embeds.append(conditional_embed)

            premium_view = get_premium_promotion_view(str(interaction.user.id))

            await interaction.followup.send(
                embeds=embeds,
                view=premium_view,
                files=[
                    discord.File(self.astrostats_img, "astrostats.png"),
                    discord.File(self.fortnite_thumbnail, "fortnite_thumbnail.png"),
                ],
            )

        except ValueError as e:
            logger.error("Validation Error: %s", e, exc_info=True)
            await send_error_embed(interaction, "Validation Error", str(e))
        except KeyError as e:
            logger.error("Data Error: Missing key in response: %s", e, exc_info=True)
            await send_error_embed(
                interaction,
                "Data Error",
                "Failed to retrieve valid Fortnite stats. Please try again later.",
            )
        except Exception as e:
            logger.error("Unexpected Error: %s", e, exc_info=True)
            await send_error_embed(
                interaction,
                "Unexpected Error",
                "An unexpected error occurred. Please try again later.",
            )

    @app_commands.command(name="compare", description="Compare two Fortnite players")
    @app_commands.describe(
        time="Season or Lifetime stats",
        name1="Epic name for player 1",
        name2="Epic name for player 2",
    )
    async def compare(
        self,
        interaction: discord.Interaction,
        time: Literal["Season", "Lifetime"],
        name1: str,
        name2: str,
    ):
        await interaction.response.defer()

        time_window = FORTNITE_TIME_MAPPING.get(time)
        if not time_window:
            await send_error_embed(
                interaction,
                "Invalid Time Window",
                "Please choose a valid time window (Season or Lifetime).",
            )
            return

        p1, p2 = await asyncio.gather(
            self._fetch_player_stats(name1, time_window),
            self._fetch_player_stats(name2, time_window),
        )

        errors = []
        if not p1:
            errors.append(f"No stats found for **{name1}**.")
        if not p2:
            errors.append(f"No stats found for **{name2}**.")
        if errors:
            await send_error_embed(interaction, "Account Not Found", "\n".join(errors), notify_logged=False)
            return

        embed = self.build_compare_embed(name1, p1, name2, p2, time)
        await interaction.followup.send(
            embed=embed,
            files=[
                discord.File(self.astrostats_img, "astrostats.png"),
                discord.File(self.fortnite_thumbnail, "fortnite_thumbnail.png"),
            ],
        )

    def build_embed(
        self,
        name: str,
        account: Dict[str, Any],
        battle_pass: Dict[str, Any],
        stats: Dict[str, Any],
        calculated_win_rate: float,
    ) -> discord.Embed:
        encoded_name = urllib.parse.quote(name)
        embed = discord.Embed(
            title=f"Fortnite - {name}",
            color=0xDD4F7A,
            url=f"https://fortnitetracker.com/profile/all/{encoded_name}",
        )
        embed.set_thumbnail(url="attachment://fortnite_thumbnail.png")

        overall = stats.get("stats", {}).get("all", {}).get("overall", {})
        embed.add_field(
            name="Account",
            value=f"Name: {account.get('name', 'N/A')}\nLevel: {battle_pass.get('level', 'N/A')}",
            inline=True,
        )
        embed.add_field(
            name="Match Placements",
            value=(
                f"Victory Royales: {overall.get('wins', 0)}\n"
                f"Top 5: {overall.get('top5', 0)}\n"
                f"Top 12: {overall.get('top12', 0)}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Kill Stats",
            value=(
                f"Kills/Deaths: {overall.get('kills', 0):,}/{overall.get('deaths', 0):,}\n"
                f"KD Ratio: {overall.get('kd', 0.0):.2f}\n"
                f"Kills Per Minute: {overall.get('killsPerMin', 0.0):.2f}\n"
                f"Kills Per Match: {overall.get('killsPerMatch', 0.0):.2f}\n"
                f"Players Outlived: {overall.get('playersOutlived', 0):,}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Match Stats",
            value=(
                f"Total Matches Played: {overall.get('matches', 0):,}\n"
                f"Win Rate: {calculated_win_rate:.2%}\n"
                f"Total Score: {overall.get('score', 0):,}\n"
                f"Score Per Minute: {overall.get('scorePerMin', 0):.0f}\n"
                f"Score Per Match: {overall.get('scorePerMatch', 0):.0f}\n"
                f"Total Minutes Played: {overall.get('minutesPlayed', 0):,}"
            ),
            inline=False,
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")
        return embed

    def build_compare_embed(
        self,
        name1: str,
        player1: Dict[str, Any],
        name2: str,
        player2: Dict[str, Any],
        time: str,
    ) -> discord.Embed:
        o1 = player1.get("overall", {})
        o2 = player2.get("overall", {})
        level1 = self._to_float(player1.get("battle_pass", {}).get("level"))
        level2 = self._to_float(player2.get("battle_pass", {}).get("level"))

        wins1 = self._to_float(o1.get("wins"))
        wins2 = self._to_float(o2.get("wins"))
        matches1 = self._to_float(o1.get("matches"))
        matches2 = self._to_float(o2.get("matches"))
        kills1 = self._to_float(o1.get("kills"))
        kills2 = self._to_float(o2.get("kills"))
        deaths1 = self._to_float(o1.get("deaths"))
        deaths2 = self._to_float(o2.get("deaths"))
        kd1 = self._to_float(o1.get("kd"))
        kd2 = self._to_float(o2.get("kd"))
        kpmatch1 = self._to_float(o1.get("killsPerMatch"))
        kpmatch2 = self._to_float(o2.get("killsPerMatch"))
        score1 = self._to_float(o1.get("score"))
        score2 = self._to_float(o2.get("score"))
        outlived1 = self._to_float(o1.get("playersOutlived"))
        outlived2 = self._to_float(o2.get("playersOutlived"))

        win_rate1 = (wins1 / matches1) if matches1 and matches1 > 0 and wins1 is not None else 0.0
        win_rate2 = (wins2 / matches2) if matches2 and matches2 > 0 and wins2 is not None else 0.0

        p1_lines = [
            f"Account: **{player1.get('account', {}).get('name', name1)}**",
            f"Period: **{time}**",
        ]
        p2_lines = [
            f"Account: **{player2.get('account', {}).get('name', name2)}**",
            f"Period: **{time}**",
        ]

        rows = [
            ("Battle Pass Level", level1, level2, self._fmt(level1), self._fmt(level2), True),
            ("Wins", wins1, wins2, self._fmt(wins1), self._fmt(wins2), True),
            ("Win Rate", win_rate1, win_rate2, self._fmt_percent(win_rate1), self._fmt_percent(win_rate2), True),
            ("Matches", matches1, matches2, self._fmt(matches1), self._fmt(matches2), True),
            ("Kills", kills1, kills2, self._fmt(kills1), self._fmt(kills2), True),
            ("Deaths", deaths1, deaths2, self._fmt(deaths1), self._fmt(deaths2), False),
            ("KD Ratio", kd1, kd2, self._fmt(kd1, decimals=2), self._fmt(kd2, decimals=2), True),
            ("Kills / Match", kpmatch1, kpmatch2, self._fmt(kpmatch1, decimals=2), self._fmt(kpmatch2, decimals=2), True),
            ("Score", score1, score2, self._fmt(score1), self._fmt(score2), True),
            ("Players Outlived", outlived1, outlived2, self._fmt(outlived1), self._fmt(outlived2), True),
        ]

        for label, v1, v2, d1, d2, higher_is_better in rows:
            p1_lines.append(f"{label}: **{d1}**")
            p2_lines.append(f"{label}: **{d2}**")

        embed = discord.Embed(
            title="Fortnite Compare",
            description=f"**{name1}** vs **{name2}**",
            color=0xDD4F7A,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url="attachment://fortnite_thumbnail.png")
        embed.add_field(name=f"Player 1: {name1}", value="\n".join(p1_lines), inline=False)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)
        embed.add_field(name=f"Player 2: {name2}", value="\n".join(p2_lines), inline=False)
        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")
        return embed

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
    def _fmt(value: Optional[float], decimals: int = 0) -> str:
        if value is None:
            return "N/A"
        if decimals == 0 and float(value).is_integer():
            return f"{int(value):,}"
        return f"{value:,.{decimals}f}"

    @staticmethod
    def _fmt_percent(value: float) -> str:
        return f"{value * 100:.2f}%"


async def setup(bot: commands.Bot):
    await bot.add_cog(FortniteCog(bot))

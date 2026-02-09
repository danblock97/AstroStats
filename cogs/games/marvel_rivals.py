import asyncio
import datetime
import logging
import os
from typing import Any, Dict, Iterable, Optional

import discord
from discord import app_commands
from discord.ext import commands

from config.constants import MARVEL_RIVALS_CURRENT_SEASON, MARVEL_RIVALS_SEASONS
from core.errors import APIError, ResourceNotFoundError, send_error_embed
from services.api.marvel_rivals import fetch_marvel_rivals_player

logger = logging.getLogger(__name__)

MARVEL_RIVALS_SEASON_CHOICES = [
    app_commands.Choice(name=label, value=season_id)
    for season_id, label in MARVEL_RIVALS_SEASONS.items()
]


class MarvelRivalsCog(commands.GroupCog, group_name="marvelrivals"):
    """A cog for Marvel Rivals stat commands."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')
        self.rank_icons_path = os.path.join(self.base_path, 'images', 'marvel_rivals', 'ranks')

    @app_commands.command(name="stats", description="Search Marvel Rivals ranked stats")
    @app_commands.describe(season="Season to query")
    @app_commands.choices(season=MARVEL_RIVALS_SEASON_CHOICES)
    async def stats(
        self,
        interaction: discord.Interaction,
        name: str,
        season: int = MARVEL_RIVALS_CURRENT_SEASON
    ):
        await interaction.response.defer()

        try:
            response = await fetch_marvel_rivals_player(name, season=season)
            embed, rank_icon_path = self.build_embed(name, response)
            season_name = MARVEL_RIVALS_SEASONS.get(season, f"Season {season}")
            embed.description = f"Season: **{season_name}**"

            files = [discord.File(self.astrostats_img, "astrostats.png")]
            if rank_icon_path:
                files.append(discord.File(rank_icon_path, "marvel_rank.png"))

            await interaction.followup.send(
                embed=embed,
                files=files
            )
        except ResourceNotFoundError:
            await send_error_embed(
                interaction,
                "Account Not Found",
                f"No Marvel Rivals stats found for **{name}**.",
                notify_logged=False
            )
        except APIError as e:
            await send_error_embed(interaction, "API Error", str(e))
        except Exception as e:
            logger.error("Unexpected error in /marvelrivals: %s", e, exc_info=True)
            await send_error_embed(
                interaction,
                "Unexpected Error",
                "An unexpected error occurred while fetching Marvel Rivals stats. Please try again later."
            )

    @app_commands.command(name="compare", description="Compare two Marvel Rivals players")
    @app_commands.describe(season="Season to query")
    @app_commands.choices(season=MARVEL_RIVALS_SEASON_CHOICES)
    async def compare(
        self,
        interaction: discord.Interaction,
        name1: str,
        name2: str,
        season: int = MARVEL_RIVALS_CURRENT_SEASON,
    ):
        await interaction.response.defer()

        results = await asyncio.gather(
            fetch_marvel_rivals_player(name1, season=season),
            fetch_marvel_rivals_player(name2, season=season),
            return_exceptions=True,
        )

        errors = []
        payloads: list[Optional[Dict[str, Any]]] = [None, None]
        for idx, result in enumerate(results):
            requested_name = name1 if idx == 0 else name2
            if isinstance(result, ResourceNotFoundError):
                errors.append(f"No Marvel Rivals stats found for **{requested_name}**.")
            elif result is None:
                errors.append(f"No Marvel Rivals stats found for **{requested_name}**.")
            elif isinstance(result, APIError):
                await send_error_embed(interaction, "API Error", str(result))
                return
            elif isinstance(result, Exception):
                logger.error("Unexpected error in /marvelrivals compare: %s", result, exc_info=True)
                await send_error_embed(
                    interaction,
                    "Unexpected Error",
                    "An unexpected error occurred while fetching Marvel Rivals stats. Please try again later.",
                )
                return
            else:
                payloads[idx] = result

        if errors:
            await send_error_embed(interaction, "Account Not Found", "\n".join(errors), notify_logged=False)
            return

        season_name = MARVEL_RIVALS_SEASONS.get(season, f"Season {season}")
        p1 = self._extract_player_summary(name1, payloads[0])
        p2 = self._extract_player_summary(name2, payloads[1])
        embed = self.build_compare_embed(p1, p2, season_name)

        await interaction.followup.send(
            embed=embed,
            files=[discord.File(self.astrostats_img, "astrostats.png")],
        )

    def build_embed(self, requested_name: str, response: Dict[str, Any]) -> tuple[discord.Embed, Optional[str]]:
        summary = self._extract_player_summary(requested_name, response)
        display_name = summary["display_name"]
        rank_icon_path = summary["rank_icon_path"]

        embed = discord.Embed(
            title=f"Marvel Rivals - {display_name}",
            color=0xE62429,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        if rank_icon_path:
            embed.set_thumbnail(url="attachment://marvel_rank.png")

        profile_lines = [
            f"Player: **{display_name}**",
            f"Level: **{self._format_value(summary['level'])}**",
            f"Rank: **{self._format_value(summary['rank'])}**",
            f"Rank Points: **{self._format_value(summary['rank_points'])}**",
        ]
        embed.add_field(name="Profile", value="\n".join(profile_lines), inline=True)

        match_lines = [
            f"Matches: **{self._format_value(summary['matches'])}**",
            f"Wins: **{self._format_value(summary['wins'])}**",
            f"Losses: **{self._format_value(summary['losses'])}**",
            f"Win Rate: **{self._format_percent(summary['win_rate'])}**",
        ]
        embed.add_field(name="Match Stats", value="\n".join(match_lines), inline=True)

        combat_lines = [
            f"Kills: **{self._format_value(summary['kills'])}**",
            f"Deaths: **{self._format_value(summary['deaths'])}**",
            f"Assists: **{self._format_value(summary['assists'])}**",
            f"KDA: **{self._format_value(summary['kda'])}**",
        ]
        embed.add_field(name="Combat Stats", value="\n".join(combat_lines), inline=False)

        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")
        return embed, rank_icon_path

    def build_compare_embed(self, player1: Dict[str, Any], player2: Dict[str, Any], season_name: str) -> discord.Embed:
        p1_lines = [
            f"Rank: **{self._format_value(player1['rank'])}**",
            f"Season: **{season_name}**",
        ]
        p2_lines = [
            f"Rank: **{self._format_value(player2['rank'])}**",
            f"Season: **{season_name}**",
        ]

        rows = [
            ("Level", player1["level_num"], player2["level_num"], self._format_value(player1["level"]), self._format_value(player2["level"]), True),
            ("Rank Points", player1["rank_points_num"], player2["rank_points_num"], self._format_value(player1["rank_points"]), self._format_value(player2["rank_points"]), True),
            ("Matches", player1["matches_num"], player2["matches_num"], self._format_value(player1["matches"]), self._format_value(player2["matches"]), True),
            ("Wins", player1["wins_num"], player2["wins_num"], self._format_value(player1["wins"]), self._format_value(player2["wins"]), True),
            ("Losses", player1["losses_num"], player2["losses_num"], self._format_value(player1["losses"]), self._format_value(player2["losses"]), False),
            ("Win Rate", player1["win_rate_num"], player2["win_rate_num"], self._format_percent(player1["win_rate"]), self._format_percent(player2["win_rate"]), True),
            ("Kills", player1["kills_num"], player2["kills_num"], self._format_value(player1["kills"]), self._format_value(player2["kills"]), True),
            ("Deaths", player1["deaths_num"], player2["deaths_num"], self._format_value(player1["deaths"]), self._format_value(player2["deaths"]), False),
            ("Assists", player1["assists_num"], player2["assists_num"], self._format_value(player1["assists"]), self._format_value(player2["assists"]), True),
            ("KDA", player1["kda_num"], player2["kda_num"], self._format_value(player1["kda"]), self._format_value(player2["kda"]), True),
        ]

        for label, v1, v2, d1, d2, higher_is_better in rows:
            p1_lines.append(f"{label}: **{d1}**")
            p2_lines.append(f"{label}: **{d2}**")

        embed = discord.Embed(
            title="Marvel Rivals Compare",
            description=f"**{player1['display_name']}** vs **{player2['display_name']}**",
            color=0xE62429,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name=f"Player 1: {player1['display_name']}", value="\n".join(p1_lines), inline=False)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)
        embed.add_field(name=f"Player 2: {player2['display_name']}", value="\n".join(p2_lines), inline=False)
        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")
        return embed

    def _extract_player_summary(self, requested_name: str, response: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        payload = response.get("data", response) if isinstance(response, dict) else {}
        player = payload.get("player", {}) if isinstance(payload, dict) else {}
        overall_stats = payload.get("overall_stats", {}) if isinstance(payload, dict) else {}

        display_name = self._first_value(payload, ("name", "playerName", "username", "ign")) or requested_name
        level = self._get_nested(player, "level") or self._first_value(payload, ("accountLevel", "playerLevel"))
        rank = self._get_nested(player, "rank", "rank") or self._first_value(payload, ("rankName", "currentRank", "tier"))
        rank_icon_path = self._resolve_rank_icon_path(player, rank)
        rank_points = self._extract_latest_rank_score(player) or self._first_value(
            payload, ("rankPoints", "rankScore", "mmr", "score", "sr", "rp")
        )

        matches = self._first_value(payload, ("total_matches", "matches", "matchesPlayed", "gamesPlayed", "totalMatches", "games"))
        wins = self._first_value(payload, ("total_wins", "wins", "win"))
        losses = self._first_value(payload, ("total_losses", "losses", "loss"))

        kills = self._first_value(payload, ("total_kills", "kills", "totalKills", "eliminations"))
        deaths = self._first_value(payload, ("total_deaths", "deaths", "totalDeaths"))
        assists = self._first_value(payload, ("total_assists", "assists", "totalAssists"))
        kda = self._first_value(payload, ("kda", "kd", "killDeathRatio"))
        win_rate = self._first_value(payload, ("winRate",))

        ranked_totals = overall_stats.get("ranked", {}) if isinstance(overall_stats, dict) else {}
        unranked_totals = overall_stats.get("unranked", {}) if isinstance(overall_stats, dict) else {}

        summed_matches = self._sum_numeric(ranked_totals.get("total_matches"), unranked_totals.get("total_matches"))
        summed_wins = self._sum_numeric(ranked_totals.get("total_wins"), unranked_totals.get("total_wins"))

        matches = self._coalesce(overall_stats.get("total_matches"), summed_matches, matches)
        wins = self._coalesce(overall_stats.get("total_wins"), summed_wins, wins)
        kills = self._coalesce(overall_stats.get("total_kills"), ranked_totals.get("total_kills"), unranked_totals.get("total_kills"), kills)
        deaths = self._coalesce(overall_stats.get("total_deaths"), ranked_totals.get("total_deaths"), unranked_totals.get("total_deaths"), deaths)
        assists = self._coalesce(overall_stats.get("total_assists"), ranked_totals.get("total_assists"), unranked_totals.get("total_assists"), assists)

        matches_num = self._to_float(matches)
        wins_num = self._to_float(wins)
        losses_num = self._to_float(losses)

        if matches_num is None and wins_num is not None and losses_num is not None:
            matches_num = wins_num + losses_num
            matches = int(matches_num)

        if losses is None and matches_num is not None and wins_num is not None:
            losses = max(0, int(matches_num - wins_num))
            losses_num = self._to_float(losses)

        if matches_num is not None and matches_num > 0 and wins_num is not None:
            win_rate = wins_num / matches_num
        elif wins_num is not None and losses_num is not None and (wins_num + losses_num) > 0:
            win_rate = wins_num / (wins_num + losses_num)

        if kda is None:
            kills_num = self._to_float(kills)
            assists_num = self._to_float(assists)
            deaths_num = self._to_float(deaths)
            if kills_num is not None and assists_num is not None and deaths_num is not None:
                if deaths_num <= 0:
                    kda = kills_num + assists_num
                else:
                    kda = (kills_num + assists_num) / deaths_num

        return {
            "display_name": display_name,
            "level": level,
            "rank": rank,
            "rank_points": rank_points,
            "matches": matches,
            "wins": wins,
            "losses": losses,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda": kda,
            "win_rate": win_rate,
            "rank_icon_path": rank_icon_path,
            "level_num": self._to_float(level),
            "rank_points_num": self._to_float(rank_points),
            "matches_num": self._to_float(matches),
            "wins_num": self._to_float(wins),
            "losses_num": self._to_float(losses),
            "kills_num": self._to_float(kills),
            "deaths_num": self._to_float(deaths),
            "assists_num": self._to_float(assists),
            "kda_num": self._to_float(kda),
            "win_rate_num": self._to_float(win_rate),
        }

    def _first_value(self, data: Any, keys: Iterable[str]) -> Optional[Any]:
        key_set = {self._normalize(k) for k in keys}
        stack = [data]

        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key, value in current.items():
                    normalized_key = self._normalize(str(key))
                    if normalized_key in key_set:
                        extracted = self._extract_scalar(value)
                        if extracted is not None:
                            return extracted

                    if isinstance(value, (dict, list)):
                        stack.append(value)
            elif isinstance(current, list):
                for item in current:
                    if isinstance(item, (dict, list)):
                        stack.append(item)

        return None

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(ch.lower() for ch in value if ch.isalnum())

    def _extract_scalar(self, value: Any) -> Optional[Any]:
        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            for key in ("value", "displayValue", "name", "title"):
                if key in value and isinstance(value[key], (str, int, float, bool)):
                    return value[key]

        return None

    @staticmethod
    def _coalesce(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    @staticmethod
    def _get_nested(data: Dict[str, Any], *path: str) -> Optional[Any]:
        current: Any = data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    def _extract_latest_rank_score(self, player: Dict[str, Any]) -> Optional[Any]:
        rank_game_season = self._get_nested(player, "info", "rank_game_season")
        if not isinstance(rank_game_season, dict) or not rank_game_season:
            return None

        latest_key = max(rank_game_season.keys())
        latest_season = rank_game_season.get(latest_key, {})
        if not isinstance(latest_season, dict):
            return None

        return latest_season.get("rank_score") or latest_season.get("max_rank_score")

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _sum_numeric(self, left: Any, right: Any) -> Optional[float]:
        left_num = self._to_float(left)
        right_num = self._to_float(right)
        if left_num is None or right_num is None:
            return None
        return left_num + right_num

    def _resolve_rank_icon_path(self, player: Dict[str, Any], rank_name: Any) -> Optional[str]:
        candidates = []

        rank_image = self._get_nested(player, "rank", "image")
        if isinstance(rank_image, str) and rank_image:
            image_filename = os.path.basename(rank_image)
            if image_filename:
                candidates.append(image_filename)

        if isinstance(rank_name, str):
            normalized_rank = rank_name.lower()
            if "one above all" in normalized_rank:
                candidates.append("one_above_all.png")
            elif "grandmaster" in normalized_rank:
                candidates.append("grandmaster.png")
            elif "celestial" in normalized_rank:
                candidates.append("celestial.png")
            elif "eternity" in normalized_rank:
                candidates.append("eternity.png")
            elif "diamond" in normalized_rank:
                candidates.append("diamond.png")
            elif "platinum" in normalized_rank:
                candidates.append("platinum.png")
            elif "gold" in normalized_rank:
                candidates.append("gold.png")
            elif "silver" in normalized_rank:
                candidates.append("silver.png")
            elif "bronze" in normalized_rank:
                candidates.append("bronze.png")

        for filename in candidates:
            icon_path = os.path.join(self.rank_icons_path, filename)
            if os.path.exists(icon_path):
                return icon_path

        return None

    @staticmethod
    def _format_value(value: Any) -> str:
        if value is None:
            return "N/A"
        if isinstance(value, float):
            return f"{value:.2f}"
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)

    def _format_percent(self, value: Any) -> str:
        if value is None:
            return "N/A"
        if isinstance(value, (int, float)):
            if 0 <= value <= 1:
                return f"{value * 100:.2f}%"
            if 1 < value <= 100:
                return f"{value:.2f}%"
        return self._format_value(value)


async def setup(bot: commands.Bot):
    await bot.add_cog(MarvelRivalsCog(bot))

import asyncio
import datetime
import logging
import urllib.parse
import os
from typing import Literal, Optional, Dict

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

from config.settings import FORTNITE_API_KEY
from config.constants import FORTNITE_TIME_MAPPING
from core.errors import send_error_embed
from core.utils import get_conditional_embed
from ui.embeds import get_premium_promotion_view
from services.compare_image import compare_image_generator, compare_values

logger = logging.getLogger(__name__)


class FortniteCog(commands.GroupCog, group_name="fortnite"):
    """A cog grouping Fortnite commands under `/fortnite`."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        # Get the absolute path to the images
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')
        self.fortnite_thumbnail = os.path.join(self.base_path, 'images', 'fortnite_thumbnail.png')

    async def fetch_fortnite_stats(self, name: str, time_window: str) -> Optional[Dict]:
        if not FORTNITE_API_KEY:
            logger.error("Fortnite API key not found. Please check your .env file.")
            return None

        url = (
            "https://fortnite-api.com/v2/stats/br/v2"
            f"?timeWindow={time_window}&name={name}"
        )
        headers = {"Authorization": FORTNITE_API_KEY}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    status = response.status
                    if status == 200:
                        return await response.json()
                    elif status == 404:
                        return None
                    else:
                        logger.error(
                            f"Failed to fetch stats for {name}. HTTP {status} received."
                        )
                        return None
            except aiohttp.ClientError as e:
                logger.error(
                    f"Client error occurred while fetching Fortnite stats: {e}",
                    exc_info=True
                )
                return None

    async def _fetch_player_stats(self, name: str, time_window: str):
        """Fetch and parse Fortnite stats for a player. Returns parsed stats dict or None."""
        data = await self.fetch_fortnite_stats(name, time_window)
        if not data or 'data' not in data:
            return None

        stats = data['data']
        account = stats.get('account', {})
        battle_pass = stats.get('battlePass', {})
        overall_stats = stats.get('stats', {}).get('all', {}).get('overall', {})
        wins = overall_stats.get('wins', 0)
        matches = overall_stats.get('matches', 0)
        calculated_win_rate = wins / matches if matches > 0 else 0

        return {
            'stats': stats,
            'account': account,
            'battle_pass': battle_pass,
            'overall': overall_stats,
            'wins': wins,
            'matches': matches,
            'win_rate': calculated_win_rate,
        }

    @app_commands.command(name="stats", description="Check your Fortnite Player Stats")
    async def stats(
            self,
            interaction: discord.Interaction,
            time: Literal['Season', 'Lifetime'],
            name: str
    ):
        try:
            await interaction.response.defer()

            time_window = FORTNITE_TIME_MAPPING.get(time)
            if not time_window:
                await send_error_embed(
                    interaction,
                    "Invalid Time Window",
                    "Please choose a valid time window (Season or Lifetime)."
                )
                return

            player = await self._fetch_player_stats(name, time_window)

            if not player:
                await send_error_embed(
                    interaction,
                    "Account Not Found",
                    (
                        f"No stats found for **{name}** for the current season. "
                        "Epic may not have updated your stats yet! Please double-check your details. "
                        "If you haven't played this season, be sure to play some games and try again later."
                    )
                )
                return

            embed = self.build_embed(name, player['account'], player['battle_pass'], player['stats'], player['win_rate'])

            conditional_embed = await get_conditional_embed(interaction, 'FORTNITE_EMBED', discord.Color.orange())
            embeds = [embed]
            if conditional_embed:
                embeds.append(conditional_embed)

            premium_view = get_premium_promotion_view(str(interaction.user.id))

            await interaction.followup.send(
                embeds=embeds,
                view=premium_view,
                files=[
                    discord.File(self.astrostats_img, "astrostats.png"),
                    discord.File(self.fortnite_thumbnail, "fortnite_thumbnail.png")
                ]
            )

        except ValueError as e:
            logger.error(f"Validation Error: {e}", exc_info=True)
            await send_error_embed(interaction, "Validation Error", str(e))

        except KeyError as e:
            logger.error(f"Data Error: Missing key in response: {e}", exc_info=True)
            await send_error_embed(
                interaction,
                "Data Error",
                "Failed to retrieve valid Fortnite stats. Please try again later."
            )

        except Exception as e:
            logger.error(f"Unexpected Error: {e}", exc_info=True)
            await send_error_embed(
                interaction,
                "Unexpected Error",
                "An unexpected error occurred. Please try again later."
            )

    @app_commands.command(name="compare", description="Compare two Fortnite players side-by-side")
    async def compare(
            self,
            interaction: discord.Interaction,
            time: Literal['Season', 'Lifetime'],
            name1: str,
            name2: str
    ):
        try:
            await interaction.response.defer()

            time_window = FORTNITE_TIME_MAPPING.get(time)
            if not time_window:
                await send_error_embed(interaction, "Invalid Time Window", "Please choose a valid time window (Season or Lifetime).")
                return

            p1, p2 = await asyncio.gather(
                self._fetch_player_stats(name1, time_window),
                self._fetch_player_stats(name2, time_window)
            )

            errors = []
            if not p1:
                errors.append(f"No stats found for **{name1}**.")
            if not p2:
                errors.append(f"No stats found for **{name2}**.")
            if errors:
                await send_error_embed(interaction, "Player Not Found", "\n".join(errors), notify_logged=False)
                return

            rows = self._build_compare_rows(p1, p2)
            img_buf = compare_image_generator.create_image(
                title="Fortnite Comparison",
                player1_name=name1,
                player2_name=name2,
                rows=rows,
                accent_color=(221, 79, 122),
                subtitle=f"Time Window: {time}",
            )

            if img_buf:
                await interaction.followup.send(
                    file=discord.File(img_buf, "fortnite_compare.png")
                )
            else:
                await send_error_embed(interaction, "Image Error", "Failed to generate comparison image.")

        except Exception as e:
            logger.error(f"Unexpected Error in compare: {e}", exc_info=True)
            await send_error_embed(interaction, "Unexpected Error", "An unexpected error occurred. Please try again later.")

    def _build_compare_rows(self, p1: Dict, p2: Dict):
        """Build comparison rows for the image generator."""
        rows = []
        o1, o2 = p1['overall'], p2['overall']

        # Level
        bp1 = p1['battle_pass'].get('level', 'N/A')
        bp2 = p2['battle_pass'].get('level', 'N/A')
        rows.append(("Level", str(bp1), str(bp2)))

        stat_keys = [
            ("Wins", 'wins', True),
            ("K/D Ratio", 'kd', True),
            ("Kills", 'kills', True),
            ("Matches", 'matches', True),
            ("Top 5", 'top5', True),
            ("Top 12", 'top12', True),
        ]

        for label, key, higher_better in stat_keys:
            v1 = o1.get(key, 0) or 0
            v2 = o2.get(key, 0) or 0
            if isinstance(v1, float) or isinstance(v2, float):
                s1, s2 = f"{v1:.2f}", f"{v2:.2f}"
            else:
                s1, s2 = f"{v1:,}", f"{v2:,}"
            s1, s2 = compare_values(v1, v2, s1, s2, higher_better)
            rows.append((label, s1, s2))

        # Win rate
        wr1, wr2 = p1['win_rate'], p2['win_rate']
        ws1 = f"{wr1:.2%}"
        ws2 = f"{wr2:.2%}"
        ws1, ws2 = compare_values(wr1, wr2, ws1, ws2)
        rows.append(("Win Rate", ws1, ws2))

        return rows

    def build_embed(self, name: str, account: Dict, battle_pass: Dict, stats: Dict,
                    calculated_win_rate: float) -> discord.Embed:
        encoded_name = urllib.parse.quote(name)
        embed = discord.Embed(
            title=f"Fortnite - {name}",
            color=0xdd4f7a,
            url=f"https://fortnitetracker.com/profile/all/{encoded_name}"
        )
        embed.set_thumbnail(url="attachment://fortnite_thumbnail.png")

        embed.add_field(
            name="Account",
            value=f"Name: {account.get('name', 'N/A')}\nLevel: {battle_pass.get('level', 'N/A')}",
            inline=True
        )
        embed.add_field(
            name="Match Placements",
            value=(
                f"Victory Royales: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('wins', 0)}\n"
                f"Top 5: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('top5', 0)}\n"
                f"Top 12: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('top12', 0)}"
            ),
            inline=True
        )
        embed.add_field(
            name="Kill Stats",
            value=(
                f"Kills/Deaths: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('kills', 0):,}/"
                f"{stats.get('stats', {}).get('all', {}).get('overall', {}).get('deaths', 0):,}\n"
                f"KD Ratio: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('kd', 0.0):.2f}\n"
                f"Kills Per Minute: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('killsPerMin', 0.0):.2f}\n"
                f"Kills Per Match: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('killsPerMatch', 0.0):.2f}\n"
                f"Players Outlived: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('playersOutlived', 0):,}"
            ),
            inline=False
        )
        embed.add_field(
            name="Match Stats",
            value=(
                f"Total Matches Played: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('matches', 0):,}\n"
                f"Win Rate: {calculated_win_rate:.2%}\n"
                f"Total Score: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('score', 0):,}\n"
                f"Score Per Minute: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('scorePerMin', 0):.0f}\n"
                f"Score Per Match: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('scorePerMatch', 0):.0f}\n"
                f"Total Minutes Played: {stats.get('stats', {}).get('all', {}).get('overall', {}).get('minutesPlayed', 0):,}"
            ),
            inline=False
        )
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")
        return embed




async def setup(bot: commands.Bot):
    await bot.add_cog(FortniteCog(bot))

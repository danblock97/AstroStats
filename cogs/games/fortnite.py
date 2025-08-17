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

logger = logging.getLogger(__name__)


class FortniteCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Get the absolute path to the images
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

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

    @app_commands.command(name="fortnite", description="Check your Fortnite Player Stats")
    async def fortnite(
            self,
            interaction: discord.Interaction,
            time: Literal['Season', 'Lifetime'],
            name: str = None
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

            time_window = FORTNITE_TIME_MAPPING.get(time)
            if not time_window:
                await send_error_embed(
                    interaction,
                    "Invalid Time Window",
                    "Please choose a valid time window (Season or Lifetime)."
                )
                return

            data = await self.fetch_fortnite_stats(name, time_window)

            if not data or 'data' not in data:
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

            stats = data['data']
            account = stats.get('account', {})
            battle_pass = stats.get('battlePass', {})

            overall_stats = stats.get('stats', {}).get('all', {}).get('overall', {})
            wins = overall_stats.get('wins', 0)
            matches = overall_stats.get('matches', 0)
            calculated_win_rate = wins / matches if matches > 0 else 0

            embed = self.build_embed(name, account, battle_pass, stats, calculated_win_rate)

            conditional_embed = await get_conditional_embed(interaction, 'FORTNITE_EMBED', discord.Color.orange())
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

    def build_embed(self, name: str, account: Dict, battle_pass: Dict, stats: Dict,
                    calculated_win_rate: float) -> discord.Embed:
        encoded_name = urllib.parse.quote(name)
        embed = discord.Embed(
            title=f"Fortnite - {name}",
            color=0xdd4f7a,
            url=f"https://fortnitetracker.com/profile/all/{encoded_name}"
        )
        embed.set_thumbnail(
            url="https://seeklogo.com/images/F/fortnite-logo-1F7897BD1E-seeklogo.com.png"
        )

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

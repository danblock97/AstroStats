import os
import datetime
import logging
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
import requests

from config.settings import TFT_API
from config.constants import LEAGUE_REGIONS, TFT_QUEUE_TYPE_NAMES
from core.utils import get_conditional_embed
from core.errors import send_error_embed

logger = logging.getLogger(__name__)


class TFTCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    @app_commands.command(name="tft", description="Check your TFT Player Stats!")
    async def tft(self, interaction: discord.Interaction, region: Literal[
        "EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2", "JP1", "KR", "OC1", "SG2", "TW2", "VN2"], riotid: str):
        try:
            await interaction.response.defer()

            if "#" not in riotid:
                await send_error_embed(
                    interaction,
                    "Invalid Format",
                    "Please enter both your game name and tag line in the format `gameName#tagLine`."
                )
                return

            game_name, tag_line = riotid.split("#")
            riot_api_key = TFT_API
            if not riot_api_key:
                logger.error("TFT API key is missing")
                await send_error_embed(
                    interaction,
                    "Configuration Error",
                    "TFT API key is not configured. Please contact the bot owner."
                )
                return

            headers = {'X-Riot-Token': riot_api_key}

            regional_url = (
                "https://europe.api.riotgames.com/riot/account/v1/accounts/"
                f"by-riot-id/{game_name}/{tag_line}"
            )
            response = requests.get(regional_url, headers=headers)

            if response.status_code == 404:
                await send_error_embed(
                    interaction,
                    "Summoner Not Found",
                    "Summoner not found. Please check your Riot ID and try again."
                )
                return

            response.raise_for_status()

            puuid = response.json().get('puuid')
            if not puuid:
                logger.error("PUUID not found in the API response.")
                await send_error_embed(
                    interaction,
                    "Data Error",
                    "Failed to retrieve summoner data. Please ensure your Riot ID is correct and try again."
                )
                return

            summoner_url = (
                f"https://{region.lower()}.api.riotgames.com/tft/summoner/v1/"
                f"summoners/by-puuid/{puuid}"
            )
            summoner_response = requests.get(summoner_url, headers=headers)
            if summoner_response.status_code != 200:
                await send_error_embed(
                    interaction,
                    "Region Error",
                    f"Failed to retrieve summoner data for the region {region}."
                )
                return

            summoner_data = summoner_response.json()
            league_url = (
                f"https://{region.lower()}.api.riotgames.com/tft/league/v1/entries/"
                f"by-summoner/{summoner_data['id']}"
            )
            league_response = requests.get(league_url, headers=headers)

            embed = discord.Embed(
                title=f"{game_name}#{tag_line} - Level {summoner_data['summonerLevel']}",
                color=0x1a78ae
            )
            embed.set_thumbnail(
                url=(
                    "https://raw.communitydragon.org/latest/game/assets/ux/summonericons/"
                    f"profileicon{summoner_data['profileIconId']}.png"
                )
            )

            if league_response.status_code == 200 and league_response.json():
                stats = league_response.json()
                for league_data in stats:
                    queue_type = TFT_QUEUE_TYPE_NAMES.get(league_data['queueType'], "Other")
                    tier = league_data['tier']
                    rank = league_data['rank']
                    lp = league_data['leaguePoints']
                    wins = league_data['wins']
                    losses = league_data['losses']
                    total_games = wins + losses
                    winrate = int((wins / total_games) * 100) if total_games > 0 else 0

                    league_info = (
                        f"{tier} {rank} {lp} LP\n"
                        f"Wins: {wins}\n"
                        f"Losses: {losses}\n"
                        f"Winrate: {winrate}%"
                    )
                    embed.add_field(
                        name=queue_type,
                        value=league_info,
                        inline=False
                    )
            else:
                embed.add_field(name="Rank", value="Unranked", inline=False)

            embed.add_field(
                name="Support Us ❤️",
                value=(
                    "[If you enjoy using this bot, consider supporting us!]"
                    "(https://buymeacoffee.com/danblock97)"
                )
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")

            # Add Conditional Embed
            conditional_embed = await get_conditional_embed(
                interaction, 'TFT_EMBED', discord.Color.orange()
            )

            embeds = [embed]
            if conditional_embed:
                embeds.append(conditional_embed)

            await interaction.followup.send(embeds=embeds)

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                await send_error_embed(
                    interaction,
                    "Summoner Not Found",
                    "Summoner not found. Please check your Riot ID and try again."
                )
            else:
                logger.error(f"HTTP Error: {e}")
                await send_error_embed(
                    interaction,
                    "API Error",
                    "An error occurred while retrieving data from the Riot API. "
                    "Please try again later."
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error: {e}")
            await send_error_embed(
                interaction,
                "Connection Error",
                "Sorry, I couldn't retrieve Teamfight Tactics stats at the moment. "
                "Please try again later."
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Data Error: {e}")
            await send_error_embed(
                interaction,
                "Data Error",
                "Failed to retrieve summoner data. Please ensure your Riot ID is correct and try again."
            )
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            await send_error_embed(
                interaction,
                "Unexpected Error",
                "Oops! An unexpected error occurred while processing your request. "
                "Please try again later."
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(TFTCog(bot))
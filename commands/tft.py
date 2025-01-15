import os
import logging
import datetime
from typing import Literal

import discord
import requests

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

REGIONS = Literal[
    "EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2",
    "JP1", "KR", "OC1", "SG2", "TW2", "VN2"
]

TFT_QUEUE_TYPE_NAMES = {
    "RANKED_TFT": "Ranked TFT",
}

async def tft(interaction: discord.Interaction, region: REGIONS, riotid: str):
    try:
        await interaction.response.defer()

        if "#" not in riotid:
            await interaction.followup.send(
                "Please enter both your game name and tag line in the format `gameName#tagLine`."
            )
            return

        game_name, tag_line = riotid.split("#")
        riot_api_key = os.getenv('TFT_API')
        headers = {'X-Riot-Token': riot_api_key}

        regional_url = (
            "https://europe.api.riotgames.com/riot/account/v1/accounts/"
            f"by-riot-id/{game_name}/{tag_line}"
        )
        response = requests.get(regional_url, headers=headers)

        if response.status_code == 404:
            await interaction.followup.send(
                "Summoner not found. Please check your Riot ID and try again."
            )
            return

        response.raise_for_status()

        puuid = response.json().get('puuid')
        if not puuid:
            logging.error("PUUID not found in the API response.")
            await interaction.followup.send(
                "Failed to retrieve summoner data. Please ensure your Riot ID is correct and try again."
            )
            return

        summoner_url = (
            f"https://{region.lower()}.api.riotgames.com/tft/summoner/v1/"
            f"summoners/by-puuid/{puuid}"
        )
        summoner_response = requests.get(summoner_url, headers=headers)
        if summoner_response.status_code != 200:
            await interaction.followup.send(
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
                embed.add_field(
                    name="Support Us ❤️",
                    value=(
                        "[If you enjoy using this bot, consider supporting us!]"
                        "(https://buymeacoffee.com/danblock97)"
                    )
                )
        else:
            embed.add_field(name="Rank", value="Unranked", inline=False)

        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")

        # ------------------------------------------------------
        # Create the Promotional Embed
        # ------------------------------------------------------
        promo_embed = discord.Embed(
            description="⭐ **New:** Squib Games Has Arrived to AstroStats! Check out `/help` for more information!",
            color=discord.Color.blue(),  # Customize the color as desired
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        promo_embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")

        # ------------------------------------------------------
        # Send Both Embeds Together
        # ------------------------------------------------------
        await interaction.followup.send(embeds=[embed, promo_embed])

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            await interaction.followup.send(
                "Summoner not found. Please check your Riot ID and try again."
            )
        else:
            logging.error(f"HTTP Error: {e}")
            await interaction.followup.send(
                "An error occurred while retrieving data from the Riot API. "
                "Please try again later."
            )
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Error: {e}")
        await interaction.followup.send(
            "Sorry, I couldn't retrieve Teamfight Tactics stats at the moment. "
            "Please try again later."
        )
    except (KeyError, ValueError) as e:
        logging.error(f"Data Error: {e}")
        await interaction.followup.send(
            "Failed to retrieve summoner data. Please ensure your Riot ID is correct and try again."
        )
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        await interaction.followup.send(
            "Oops! An unexpected error occurred while processing your request. "
            "Please try again later."
        )

async def setup(client: discord.Client):
    client.tree.add_command(
        discord.app_commands.Command(
            name="tft",
            description="Check your TFT Player Stats!",
            callback=tft
        )
    )

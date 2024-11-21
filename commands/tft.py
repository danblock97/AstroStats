import discord
import datetime
import requests
import os
import logging
from typing import Literal

# Configure logging to only log errors
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Define region options using Literal for dropdown
REGIONS = Literal["EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2", "JP1", "KR", "OC1", "PH2", "SG2", "TH2", "TW2", "VN2"]

# Mapping TFT queue types to user-friendly names
TFT_QUEUE_TYPE_NAMES = {
    "RANKED_TFT": "Ranked TFT",
}

async def tft(interaction: discord.Interaction, region: REGIONS, riotid: str):
    try:
        await interaction.response.defer()

        # Check if the riotid includes both gameName and tagLine
        if "#" not in riotid:
            await interaction.followup.send("Please enter both your game name and tag line in the format `gameName#tagLine`.")
            return

        game_name, tag_line = riotid.split("#")
        riot_api_key = os.getenv('TFT_API')  # Ensure your environment variable is set correctly
        headers = {'X-Riot-Token': riot_api_key}

        # Default routing value for account-v1 endpoint set to americas
        regional_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        response = requests.get(regional_url, headers=headers)

        if response.status_code == 404:
            await interaction.followup.send("Summoner not found. Please check your Riot ID and try again.")
            return

        response.raise_for_status()

        puuid = response.json().get('puuid')
        if not puuid:
            logging.error("PUUID not found in the API response.")
            await interaction.followup.send("Failed to retrieve summoner data. Please ensure your Riot ID is correct and try again.")
            return

        # Fetch summoner data from the selected region
        summoner_url = f"https://{region.lower()}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
        summoner_response = requests.get(summoner_url, headers=headers)

        if summoner_response.status_code != 200:
            await interaction.followup.send(f"Failed to retrieve summoner data for the region {region}.")
            return

        summoner_data = summoner_response.json()

        # Fetch league data
        league_url = f"https://{region.lower()}.api.riotgames.com/tft/league/v1/entries/by-summoner/{summoner_data['id']}"
        league_response = requests.get(league_url, headers=headers)

        # Build the embed message
        embed = discord.Embed(title=f"{game_name}#{tag_line} - Level {summoner_data['summonerLevel']}", color=0x1a78ae)
        embed.set_thumbnail(
            url=f"https://raw.communitydragon.org/latest/game/assets/ux/summonericons/profileicon{summoner_data['profileIconId']}.png")

        if league_response.status_code == 200 and league_response.json():
            # Player has ranked stats
            stats = league_response.json()
            for league_data in stats:
                queue_type = league_data['queueType']
                user_friendly_queue_type = TFT_QUEUE_TYPE_NAMES.get(queue_type, "Other")
                tier = league_data['tier']
                rank = league_data['rank']
                lp = league_data['leaguePoints']
                wins = league_data['wins']
                losses = league_data['losses']
                total_games = wins + losses
                winrate = int((wins / total_games) * 100) if total_games > 0 else 0

                league_info = f"{tier} {rank} {lp} LP\nWins: {wins}\nLosses: {losses}\nWinrate: {winrate}%"
                embed.add_field(name=user_friendly_queue_type, value=league_info, inline=False)

                embed.add_field(name="Support Us ❤️",
                                value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)")
        else:
            # Player is unranked
            embed.add_field(name="Rank", value="Unranked", inline=False)

        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")

        await interaction.followup.send(embed=embed)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            await interaction.followup.send("Summoner not found. Please check your Riot ID and try again.")
        else:
            logging.error(f"HTTP Error: {e}")
            await interaction.followup.send("An error occurred while retrieving data from the Riot API. Please try again later.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Request Error: {e}")
        await interaction.followup.send("Sorry, I couldn't retrieve Teamfight Tactics stats at the moment. Please try again later.")

    except (KeyError, ValueError) as e:
        logging.error(f"Data Error: {e}")
        await interaction.followup.send("Failed to retrieve summoner data. Please ensure your Riot ID is correct and try again.")

    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        await interaction.followup.send("Oops! An unexpected error occurred while processing your request. Please try again later.")

# Setup function for the bot
async def setup(client: discord.Client):
    client.tree.add_command(
        discord.app_commands.Command(
            name="tft",
            description="Check your TFT Player Stats!",
            callback=tft
        )
    )

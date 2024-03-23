import discord
import datetime
import requests
from typing import Literal
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

REGION_TO_PLATFORM = {
    "EUROPE": ["EUW1", "EUN1", "TR1", "RU"],
    "AMERICAS": ["NA1", "BR1", "LA1", "LA2"],
    "ASIA": ["JP1", "KR"],
    "SEA": ["OC1", "PH2", "SG2", "TH2", "TW2", "VN2"]
}

async def league(interaction: discord.Interaction, region: Literal['EUROPE', 'AMERICAS', 'ASIA', 'SEA'], *, name: str):
    await interaction.response.defer()

    if region not in REGION_TO_PLATFORM:
        await interaction.followup.send("Invalid region. Please use a valid regional routing value.")
        return

    try:
        platform_regions = REGION_TO_PLATFORM[region]
        gameName, tagLine = name.split("#")
        riot_api_key = os.getenv('LOL_API')
        headers = {'X-Riot-Token': riot_api_key}

        puuid = None
        # Fetch PUUID using the regional endpoint
        for platform_region in platform_regions:
            regional_url = f"https://{region.lower()}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
            response = requests.get(regional_url, headers=headers)
            if response.status_code == 200:
                puuid = response.json().get('puuid')
                break
            else:
                logging.warning(f"Failed to retrieve PUUID from {regional_url}, status code: {response.status_code}")

        if puuid is None:
            await interaction.response.send_message("Failed to retrieve summoner data. The summoner may not exist. Please ensure your name is your full tag for example (gameName#0001)")
            return

        summoner_data = None
        # Initialize a variable to store the platform where summoner data was found
        summoner_platform = None

        # Find the correct platform for summoner data
        for platform_region in platform_regions:
            summoner_url = f"https://{platform_region.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            summoner_response = requests.get(summoner_url, headers=headers)
            if summoner_response.status_code == 200:
                summoner_data = summoner_response.json()
                summoner_platform = platform_region  # Store the platform where the data was found
                break

        if not summoner_data:
            await interaction.response.send_message("Failed to retrieve detailed summoner data.")
            return
        
        # Extract summoner level and profile icon ID from the summoner data
        summoner_level = summoner_data['summonerLevel']
        profile_icon_id = summoner_data['profileIconId']

        # Now use 'summoner_platform' for league data request to ensure consistency
        league_url = f"https://{summoner_platform.lower()}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_data['id']}"
        league_response = requests.get(league_url, headers=headers)
        if league_response.status_code == 200:
            stats = league_response.json()

        if not stats:
            await interaction.response.send_message("Failed to retrieve league data.")
            return

                # Continue processing league data for the embed message
        league_data_list = []
        for league_data in stats:
            queue_type = league_data['queueType']
            tier = league_data['tier']
            rank = league_data['rank']
            lp = league_data['leaguePoints']
            wins = int(league_data['wins'])
            losses = int(league_data['losses'])
            wr = int((wins / (wins + losses)) * 100)
            league_data_list.append((queue_type, f"{tier} {rank} {lp} LP \nWin/Loss: {wins}W/{losses}L \nWinrate: {wr}%"))

        # Create and configure the Discord embed
        embed = discord.Embed(
            title=f"{gameName}#{tagLine} - Level {summoner_level}", color=0xdd4f7a
        )
        embed.set_thumbnail(
            url=f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{profile_icon_id}.jpg"
        )

        for queue_type, league_data_str in league_data_list:
            if queue_type == "RANKED_SOLO_5x5":
                embed.add_field(name="Ranked Solo/Duo", value=league_data_str)
            elif queue_type == "RANKED_FLEX_SR":
                embed.add_field(name="Ranked Flex", value=league_data_str, inline=True)

        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="Built By Goldiez ❤️")

        # Send the embed as a response
        await interaction.followup.send(embed=embed)

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error occurred: {e}")
        await interaction.followup.send("Sorry, I couldn't retrieve League of Legends stats at the moment. Please try again later.")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        await interaction.followup.send("Oops! An unexpected error occurred while processing your request. Please try again later.")

def setup(client):
    client.tree.command(
        name="league", description="Check your LoL Player Stats"
    )(league)
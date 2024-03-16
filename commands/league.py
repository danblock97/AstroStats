import discord
import datetime
import requests
from typing import Literal
import os

REGION_TO_PLATFORM = {
    "EUROPE": ["EUW1", "EUN1", "TR1", "RU"],
    "AMERICAS": ["BR1", "LA1", "LA2", "NA1"],
    "ASIA": ["JP1", "KR", "SG2", "TH2", "TW2", "VN2"]
}

async def league(interaction: discord.Interaction, region: Literal['EUROPE', 'AMERICAS', 'ASIA'], *, name: str):
    if region not in REGION_TO_PLATFORM:
        await interaction.response.send_message("Invalid region. Please use a valid regional routing value.")
        return

    try:
        platform_regions = REGION_TO_PLATFORM[region]

        gameName, tagLine = name.split("#")

        riot_api_key = os.getenv('RIOT_API')

        headers = {
            'X-Riot-Token': riot_api_key
        }

        puuid = None
        for platform_region in platform_regions:
            regional_url = f"https://{region.lower()}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
            response = requests.get(regional_url, headers=headers)
            if response.status_code == 200:
                puuid = response.json().get('puuid')
                break
        if puuid is None:
            await interaction.response.send_message("Failed to retrieve summoner data. The summoner may not exist. Please ensure your name is your full tag for example (gameName#0001)")
            return

        summoner_response = requests.get(f"https://{platform_regions[0].lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}", headers=headers)
        summoner_response.raise_for_status()
        summoner_data = summoner_response.json()

        profile_icon_id = summoner_data['profileIconId']
        summoner_level = summoner_data['summonerLevel']

        league_response = requests.get(f"https://{platform_regions[0].lower()}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_data['id']}", headers=headers)
        league_response.raise_for_status()
        stats = league_response.json()

        league_data_list = []
        for league_data in stats:
            queue_type = league_data['queueType']
            tier = league_data['tier']
            rank = league_data['rank']
            lp = league_data['leaguePoints']
            wins = int(league_data['wins'])
            losses = int(league_data['losses'])
            wr = int((wins / (wins + losses)) * 100)
            league_data_list.append((queue_type, f"{tier} {rank} {lp} LP \n Win/Loss: {wins}W/{losses}L \n Winrate: {wr}%"))

        embed = discord.Embed(
            title=f"{gameName}#{tagLine} - Level {summoner_level}", color=0xdd4f7a)

        embed.set_thumbnail(
            url=f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{profile_icon_id}.jpg")

        for queue_type, league_data_str in league_data_list:
            if queue_type == "RANKED_SOLO_5x5":
                embed.add_field(name=f"Ranked Solo/Duo",
                                value=league_data_str)
            elif queue_type == "RANKED_FLEX_SR":
                embed.add_field(name=f"Ranked Flex",
                                value=league_data_str, inline=True)

        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="Built By Goldiez ❤️")

        await interaction.response.send_message(embed=embed)

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Sorry, I couldn't retrieve League of Legends stats at the moment. Please try again later.")

    except (KeyError, ValueError) as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Failed to retrieve League of Legends stats. The service may be currently unavailable.")

    except Exception as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Oops! An unexpected error occurred while processing your request. Please try again later.")

def setup(client):
    client.tree.command(
        name="league", description="Check your LoL Player Stats"
    )(league)

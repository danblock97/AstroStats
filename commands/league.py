import discord
import datetime
import requests
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# List all regions individually
REGIONS = [
    "EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2",
    "JP1", "KR", "OC1", "PH2", "SG2", "TH2", "TW2", "VN2"
]

# Mapping queue types to user-friendly names
QUEUE_TYPE_NAMES = {
    "RANKED_SOLO_5x5": "Ranked Solo/Duo",
    "RANKED_FLEX_SR": "Ranked Flex 5v5",
}


async def league(interaction: discord.Interaction, riotid: str):
    await interaction.response.defer()

    # Check if the riotid includes both gameName and tagLine
    if "#" not in riotid:
        await interaction.followup.send("Please enter both your game name and tag line in the format gameName#tagLine.")
        return

    game_name, tag_line = riotid.split("#")
    riot_api_key = os.getenv('LOL_API')  # Make sure to set your environment variable accordingly
    headers = {'X-Riot-Token': riot_api_key}

    # Default routing value for account-v1 endpoint set to americas
    regional_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    response = requests.get(regional_url, headers=headers)
    if response.status_code == 200:
        puuid = response.json().get('puuid')
    else:
        logging.warning(f"Failed to retrieve PUUID from {regional_url}, status code: {response.status_code}")
        await interaction.followup.send("Failed to retrieve summoner data. Please ensure your Riot ID is correct.")
        return

    stats = None
    for region in REGIONS:
        summoner_url = f"https://{region.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        summoner_response = requests.get(summoner_url, headers=headers)
        if summoner_response.status_code == 200:
            summoner_data = summoner_response.json()

            # Attempt to fetch league data for the current region
            league_url = f"https://{region.lower()}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_data['id']}"
            league_response = requests.get(league_url, headers=headers)
            if league_response.status_code == 200 and league_response.json():
                # League data found, store it and break out of the loop
                stats = league_response.json()
                break
        else:
            logging.info(f"Trying next region...")

    if not stats:
        await interaction.followup.send(
            "Failed to retrieve league data. Player might not be active in the checked regions.")
        return

    # Processing league data for the embed message
    embed = discord.Embed(title=f"{game_name}#{tag_line} - Level {summoner_data['summonerLevel']}", color=0x1a78ae)
    embed.set_thumbnail(
        url=f"https://raw.communitydragon.org/latest/game/assets/ux/summonericons/profileicon{summoner_data['profileIconId']}.png")

    for league_data in stats:
        queue_type = league_data['queueType']
        user_friendly_queue_type = QUEUE_TYPE_NAMES.get(queue_type, "Other")
        tier = league_data['tier']
        rank = league_data['rank']
        lp = league_data['leaguePoints']
        wins = league_data['wins']
        losses = league_data['losses']
        winrate = int((wins / (wins + losses)) * 100)

        league_info = f"{tier} {rank} {lp} LP\nWins: {wins}\nLosses: {losses}\nWinrate: {winrate}%"
        embed.add_field(name=user_friendly_queue_type, value=league_info, inline=True)
        embed.timestamp = datetime.datetime.now(datetime.UTC)
        embed.set_footer(text="Built By Goldiez ❤️")

    await interaction.followup.send(embed=embed)


def setup(client):
    client.tree.command(
        name="league", description="Check your LoL Player Stats"
    )(league)

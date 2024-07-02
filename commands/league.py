import discord
import datetime
import aiohttp
import os
import logging
import asyncio
from collections import defaultdict

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

# Dictionary to store the last fetch time for each user
last_fetch_times = defaultdict(lambda: datetime.datetime.min)


async def fetch_data(url, headers=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logging.error(f"Error fetching data from {url}: {response.status}")
                return None
            return await response.json()


async def fetch_game_name_tagline(puuid, headers):
    regional_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    return await fetch_data(regional_url, headers)


async def fetch_summoner_data(puuid, region, headers):
    summoner_url = f"https://{region.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return await fetch_data(summoner_url, headers)


async def fetch_league_data(summoner_id, region, headers):
    league_url = f"https://{region.lower()}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    return await fetch_data(league_url, headers)


async def get_player_rank(puuid, region, headers):
    summoner_data = await fetch_summoner_data(puuid, region, headers)
    if not summoner_data:
        return "Unranked"

    summoner_id = summoner_data.get('id')
    league_data = await fetch_league_data(summoner_id, region, headers)
    if not league_data:
        return "Unranked"

    for entry in league_data:
        if entry['queueType'] == 'RANKED_SOLO_5x5':
            tier = entry.get('tier', 'Unranked').capitalize()
            rank = entry.get('rank', '').upper()
            lp = entry.get('leaguePoints', 0)
            return f"{tier} {rank} {lp} LP"
    return "Unranked"


async def fetch_champion_name(champion_id):
    url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champions/{champion_id}.json"
    data = await fetch_data(url)
    if data and 'name' in data:
        return data['name']
    return "Unknown"


async def update_live_game_view(interaction: discord.Interaction, embed, puuid, region, headers, live_game_button, game_name, tag_line, view):
    riot_api_key = os.getenv('LOL_API')
    headers = {'X-Riot-Token': riot_api_key}

    live_game_url = f"https://{region.lower()}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
    live_game_data = await fetch_data(live_game_url, headers)

    if not live_game_data or 'status' in live_game_data:
        await interaction.followup.send("No live game data found.", ephemeral=True)
        return

    blue_team = []
    red_team = []

    for player in live_game_data['participants']:
        player_puuid = player['puuid']
        account_data = await fetch_game_name_tagline(player_puuid, headers)
        if account_data:
            game_name = account_data.get('gameName')
            tag_line = account_data.get('tagLine')
            summoner_name = f"{game_name}#{tag_line}"
        else:
            summoner_name = "Unknown"

        rank = await get_player_rank(player_puuid, region, headers)

        champion_id = player['championId']
        champion_name = await fetch_champion_name(champion_id)

        player_data = {
            'summoner_name': summoner_name,
            'champion_name': champion_name,
            'rank': rank
        }

        if player['teamId'] == 100:
            blue_team.append(player_data)
        else:
            red_team.append(player_data)

    embed.clear_fields()
    embed.title = f"Live Game"

    blue_team_champions = '\n'.join([p['champion_name'] for p in blue_team])
    blue_team_names = '\n'.join([p['summoner_name'] for p in blue_team])
    blue_team_ranks = '\n'.join([p['rank'] for p in blue_team])

    red_team_champions = '\n'.join([p['champion_name'] for p in red_team])
    red_team_names = '\n'.join([p['summoner_name'] for p in red_team])
    red_team_ranks = '\n'.join([p['rank'] for p in red_team])

    embed.add_field(name="Blue Team", value=blue_team_champions, inline=True)
    embed.add_field(name="Riot ID", value=blue_team_names, inline=True)
    embed.add_field(name="Rank", value=blue_team_ranks, inline=True)

    embed.add_field(name="Red Team", value=red_team_champions, inline=True)
    embed.add_field(name="Riot ID", value=red_team_names, inline=True)
    embed.add_field(name="Rank", value=red_team_ranks, inline=True)

    await interaction.followup.send(embed=embed)

    # Update button back to 'Live Game' and enable it
    live_game_button.label = 'Live Game'
    live_game_button.disabled = False
    await interaction.edit_original_response(view=view)

    # Store the current timestamp for this user
    last_fetch_times[puuid] = datetime.datetime.utcnow()


async def update_profile_view(interaction: discord.Interaction, embed, game_name, tag_line, summoner_data, league_data,
                              puuid, region, headers):
    embed.clear_fields()  # Clear existing fields in the embed

    embed.title = f"{game_name}#{tag_line} - Level {summoner_data['summonerLevel']}"
    embed.set_thumbnail(
        url=f"https://raw.communitydragon.org/latest/game/assets/ux/summonericons/profileicon{summoner_data['profileIconId']}.png")

    for league in league_data:
        queue_type = league['queueType']
        user_friendly_queue_type = QUEUE_TYPE_NAMES.get(queue_type, "Other")
        tier = league.get('tier', 'Unranked').capitalize()
        rank = league.get('rank', '').upper()
        lp = league.get('leaguePoints', 0)
        wins = league.get('wins', 0)
        losses = league.get('losses', 0)
        winrate = int((wins / (wins + losses)) * 100) if (wins + losses) > 0 else 0

        league_info = f"{tier} {rank} {lp} LP\nWins: {wins}\nLosses: {losses}\nWinrate: {winrate}%"
        embed.add_field(name=user_friendly_queue_type, value=league_info, inline=True)

    embed.timestamp = datetime.datetime.now(datetime.UTC)
    embed.set_footer(text="Built By Goldiez ❤️ Visit riftspy.vercel.app to view your LoL Profile Today!")
    await interaction.followup.send(embed=embed,
                                    view=create_live_game_view(interaction.client, embed, puuid, region, headers, game_name, tag_line))


def create_live_game_view(client, embed, puuid, region, headers, game_name, tag_line):
    view = discord.ui.View()
    live_game_button = discord.ui.Button(label="Live Game", style=discord.ButtonStyle.primary)

    async def live_game_callback(interaction: discord.Interaction):
        current_time = datetime.datetime.utcnow()
        last_fetch_time = last_fetch_times[puuid]

        if (current_time - last_fetch_time).total_seconds() < 120:
            await interaction.response.send_message('You just fetched, try again in 2 minutes.', ephemeral=True)
            return

        live_game_button.label = "Fetching..."
        live_game_button.disabled = True
        await interaction.response.edit_message(view=view)
        await update_live_game_view(interaction, embed, puuid, region, headers, live_game_button, game_name, tag_line, view)

    live_game_button.callback = live_game_callback
    view.add_item(live_game_button)
    return view


async def league(interaction: discord.Interaction, riotid: str):
    try:
        await interaction.response.defer()

        # Check if the riotid includes both gameName and tagLine
        if "#" not in riotid:
            await interaction.followup.send(
                "Please enter both your game name and tag line in the format gameName#tagLine.")
            return

        game_name, tag_line = riotid.split("#")
        riot_api_key = os.getenv('LOL_API')
        headers = {'X-Riot-Token': riot_api_key}

        # Fetch account data to get puuid
        regional_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        account_data = await fetch_data(regional_url, headers)

        puuid = account_data.get('puuid')
        if not puuid:
            await interaction.followup.send(
                "Failed to retrieve PUUID. Please ensure your Riot ID is correct and try again.")
            return

        summoner_data = None
        league_data = None
        selected_region = None
        for region in REGIONS:
            summoner_url = f"https://{region.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            summoner_data = await fetch_data(summoner_url, headers)
            if summoner_data:
                league_url = f"https://{region.lower()}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_data['id']}"
                league_data = await fetch_data(league_url, headers)
                if league_data:
                    selected_region = region
                    break

        if not league_data:
            await interaction.followup.send(
                "Failed to retrieve league data. Player might not be active in the checked regions.")
            return

        embed = discord.Embed(title=f"{game_name}#{tag_line} - Level {summoner_data['summonerLevel']}", color=0x1a78ae)
        embed.set_thumbnail(
            url=f"https://raw.communitydragon.org/latest/game/assets/ux/summonericons/profileicon{summoner_data['profileIconId']}.png")

        for league in league_data:
            queue_type = league['queueType']
            user_friendly_queue_type = QUEUE_TYPE_NAMES.get(queue_type, "Other")
            tier = league.get('tier', 'Unranked').capitalize()
            rank = league.get('rank', '').upper()
            lp = league.get('leaguePoints', 0)
            wins = league.get('wins', 0)
            losses = league.get('losses', 0)
            winrate = int((wins / (wins + losses)) * 100) if (wins + losses) > 0 else 0

            league_info = f"{tier} {rank} {lp} LP\nWins: {wins}\nLosses: {losses}\nWinrate: {winrate}%"
            embed.add_field(name=user_friendly_queue_type, value=league_info, inline=True)

        embed.timestamp = datetime.datetime.now(datetime.UTC)
        embed.set_footer(text="Built By Goldiez ❤️ Visit riftspy.vercel.app to view your LoL Profile Today!")

        view = create_live_game_view(interaction.client, embed, puuid, selected_region, headers, game_name, tag_line)

        await interaction.followup.send(embed=embed, view=view)

    except aiohttp.ClientError as e:
        logging.error(f"Request Error: {e}")
        await interaction.followup.send(
            "Sorry, I couldn't retrieve League of Legends stats at the moment. Please try again later.")
    except (KeyError, ValueError) as e:
        logging.error(f"Data Error: {e}")
        await interaction.followup.send(
            "Failed to retrieve summoner data. Please ensure your Riot ID is correct and try again.")
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        await interaction.followup.send(
            "Oops! An unexpected error occurred while processing your request. Please try again later.")


def setup(client):
    client.tree.command(name="league", description="Check your LoL Player Stats")(league)

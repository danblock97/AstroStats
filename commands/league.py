import discord
import datetime
from typing import Literal
import aiohttp
import os
import logging
from collections import defaultdict
import asyncio
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# List all regions for dropdown
REGIONS = Literal[
    "EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2",
    "JP1", "KR", "OC1", "PH2", "SG2", "TH2", "TW2", "VN2"
]

# Mapping queue types to user-friendly names
QUEUE_TYPE_NAMES = {
    "RANKED_SOLO_5x5": "Ranked Solo/Duo",
    "RANKED_FLEX_SR": "Ranked Flex 5v5",
    "CHERRY": "Arena"
}

# Dictionary to store the last fetch time for each user
last_fetch_times = defaultdict(lambda: datetime.datetime.min)
last_game_ids = defaultdict(lambda: None)  # To track if the game has changed

# Simple in-memory cache for account data to reduce API calls
account_data_cache = {}
CACHE_EXPIRY_SECONDS = 300  # Cache expiry time in seconds

# Global dictionary to store emojis
emojis = {}

# Special champion names mapping for emojis
SPECIAL_EMOJI_NAMES = {
    "Renata Glasc": "Renata",
    "Wukong": "MonkeyKing",
    "Miss Fortune": "MissFortune",
    "Xin Zhao": "XinZhao",
    "Aurelion Sol": "AurelionSol",
    "Bel'Veth": "Belveth",
    "Cho'Gath": "Chogath",
    "Nunu & Willump": "Nunu",
    "Lee Sin": "LeeSin",
    "K'Sante": "KSante"
}

# Helper function to fetch data from an API
async def fetch_data(session: aiohttp.ClientSession, url: str, headers=None) -> dict:
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return None  # No need to log 404 errors for unavailable resources
            elif response.status == 429:
                # Rate limit exceeded, wait and retry
                retry_after = int(response.headers.get('Retry-After', '1'))
                logging.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                await asyncio.sleep(retry_after)
                return await fetch_data(session, url, headers)  # Retry the request
            else:
                logging.error(f"Error fetching data from {url}: {response.status} - {response.reason}")
                return None
    except Exception as e:
        logging.error(f"Exception during fetch_data: {e}")
        return None

# Helper function to fetch summoner data by PUUID
async def fetch_summoner_data(session: aiohttp.ClientSession, puuid: str, region: str, headers: dict) -> dict:
    summoner_url = f"https://{region.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return await fetch_data(session, summoner_url, headers)

# Helper function to fetch league data by summoner ID
async def fetch_league_data(session: aiohttp.ClientSession, summoner_id: str, region: str, headers: dict) -> dict:
    league_url = f"https://{region.lower()}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    return await fetch_data(session, league_url, headers)

# Helper function to fetch live game data by PUUID (updated to use v5 and PUUID)
async def fetch_live_game(session: aiohttp.ClientSession, puuid: str, region: str, headers: dict) -> dict:
    live_game_url = f"https://{region.lower()}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
    return await fetch_data(session, live_game_url, headers)

# Helper function to send error embed
async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=f"{description}\n\nFor more assistance, visit [AstroStats Support](https://astrostats.vercel.app)",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    await interaction.followup.send(embed=embed)

# Main League of Legends command with region selection and Riot ID
@discord.app_commands.command(name="league", description="Check your League of Legends Player Stats")
async def league(interaction: discord.Interaction, region: REGIONS, riotid: str):
    try:
        await interaction.response.defer()

        # Validate Riot ID format
        if "#" not in riotid:
            await send_error_embed(interaction, "Invalid Riot ID", "Please enter your Riot ID in the format gameName#tagLine.")
            return

        game_name, tag_line = riotid.split("#")
        riot_api_key = os.getenv('LOL_API')
        if not riot_api_key:
            await send_error_embed(interaction, "Configuration Error", "Riot API key is not configured.")
            return
        headers = {'X-Riot-Token': riot_api_key}

        # Fetch PUUID
        regional_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        async with aiohttp.ClientSession() as session:
            account_data = await fetch_data(session, regional_url, headers)
            puuid = account_data.get('puuid') if account_data else None

            if not puuid:
                await send_error_embed(interaction, "Account Not Found", "Failed to retrieve PUUID. Please ensure your Riot ID is correct.")
                return

            # Fetch summoner data from selected region
            summoner_data = await fetch_summoner_data(session, puuid, region, headers)
            if not summoner_data:
                await send_error_embed(interaction, "No Data Found", "Failed to retrieve summoner data.")
                return

            # Fetch the league data
            league_data = await fetch_league_data(session, summoner_data['id'], region, headers)

            # Build the embed message
            embed = discord.Embed(title=f"{game_name}#{tag_line} - Level {summoner_data['summonerLevel']}", color=0x1a78ae)
            embed.set_thumbnail(url=f"https://raw.communitydragon.org/latest/game/assets/ux/summonericons/profileicon{summoner_data['profileIconId']}.png")

            if league_data:
                for league in league_data:
                    queue_type = QUEUE_TYPE_NAMES.get(league['queueType'], "Other")
                    tier = league.get('tier', 'Unranked').capitalize()
                    rank = league.get('rank', '').upper()
                    lp = league.get('leaguePoints', 0)
                    wins = league.get('wins', 0)
                    losses = league.get('losses', 0)
                    winrate = int((wins / (wins + losses)) * 100) if (wins + losses) > 0 else 0
                    league_info = f"{tier} {rank} {lp} LP\nWins: {wins}\nLosses: {losses}\nWinrate: {winrate}%"
                    embed.add_field(name=queue_type, value=league_info, inline=True)
            else:
                embed.add_field(name="Rank", value="Unranked", inline=False)

            embed.add_field(name="Support Us ❤️",
                            value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)")

            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.set_footer(text="Built By Goldiez ❤️ Visit clutchgg.lol for more!")

            # Add live game data if applicable
            view = create_live_game_view(interaction.client, embed, puuid, region, headers, game_name, tag_line)
            await interaction.followup.send(embed=embed, view=view)

    except aiohttp.ClientError as e:
        logging.error(f"Request Error: {e}")
        await send_error_embed(interaction, "API Error", "Sorry, I couldn't retrieve League of Legends stats at the moment. Please try again later.")
    except (KeyError, ValueError) as e:
        logging.error(f"Data Error: {e}")
        await send_error_embed(interaction, "Data Error", "Failed to retrieve summoner data. Please ensure your Riot ID is correct.")
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        await send_error_embed(interaction, "Unexpected Error", "An unexpected error occurred while processing your request. Please try again later.")

# Helper function to create live game view
def create_live_game_view(client, embed, puuid, region, headers, game_name, tag_line):
    view = discord.ui.View()
    live_game_button = discord.ui.Button(label="Live Game", style=discord.ButtonStyle.primary)

    async def live_game_callback(interaction: discord.Interaction):
        live_game_button.label = "Fetching..."
        live_game_button.disabled = True
        await interaction.response.edit_message(view=view)

        async with aiohttp.ClientSession() as session:
            await update_live_game_view(interaction, embed, puuid, region, headers, live_game_button, game_name, tag_line, view, session)

    live_game_button.callback = live_game_callback
    view.add_item(live_game_button)
    return view

# Function to update live game view
async def update_live_game_view(interaction: discord.Interaction, embed, puuid, region, headers, live_game_button, game_name, tag_line, view, session):
    live_game_data = await fetch_live_game(session, puuid, region, headers)

    if not live_game_data or 'status' in live_game_data:
        # No live game found
        no_game_embed = discord.Embed(
            title="No Live Game Found",
            description="It seems you're not in a live game. Please try again when you're in the loading screen.",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        await interaction.followup.send(embed=no_game_embed)
        live_game_button.disabled = False
        live_game_button.label = "Live Game"
        await interaction.edit_original_response(view=view)
        return

    game_id = live_game_data['gameId']
    if last_game_ids[puuid] == game_id:
        await interaction.followup.send("No new game data since last fetch.", ephemeral=True)
    else:
        last_game_ids[puuid] = game_id
        await process_game_data(interaction, embed, live_game_data, puuid, region, headers, session)

    live_game_button.disabled = False
    live_game_button.label = 'Live Game'
    await interaction.edit_original_response(view=view)

    last_fetch_times[puuid] = datetime.datetime.utcnow()

# Process live game data
async def process_game_data(interaction: discord.Interaction, embed: discord.Embed, live_game_data: dict, puuid: str, region: str, headers: dict, session: aiohttp.ClientSession):
    blue_team = []
    red_team = []

    # Create tasks to fetch participant data concurrently
    tasks = []
    for player in live_game_data['participants']:
        tasks.append(fetch_participant_data(player, region, headers, session))

    participants_data = await asyncio.gather(*tasks)

    for player_data, team_id in participants_data:
        if team_id == 100:
            blue_team.append(player_data)
        else:
            red_team.append(player_data)

    # Build the embed message
    embed.clear_fields()
    embed.title = "Live Game"

    # Prepare the team data strings
    blue_team_champions = '\n'.join([f"{await get_emoji_for_champion(p['champion_name'])} {p['champion_name']}" for p in blue_team])
    blue_team_names = '\n'.join([p['summoner_name'] for p in blue_team])
    blue_team_ranks = '\n'.join([p['rank'] for p in blue_team])

    red_team_champions = '\n'.join([f"{await get_emoji_for_champion(p['champion_name'])} {p['champion_name']}" for p in red_team])
    red_team_names = '\n'.join([p['summoner_name'] for p in red_team])
    red_team_ranks = '\n'.join([p['rank'] for p in red_team])

    embed.add_field(name="Blue Team", value=blue_team_champions or "No data", inline=True)
    embed.add_field(name="Summoner Names", value=blue_team_names or "No data", inline=True)
    embed.add_field(name="Rank", value=blue_team_ranks or "No data", inline=True)

    embed.add_field(name="Red Team", value=red_team_champions or "No data", inline=True)
    embed.add_field(name="Summoner Names", value=red_team_names or "No data", inline=True)
    embed.add_field(name="Rank", value=red_team_ranks or "No data", inline=True)

    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text="Live Game Data")

    await interaction.followup.send(embed=embed)

# Fetch participant data
async def fetch_participant_data(player, region, headers, session):
    player_puuid = player['puuid']
    team_id = player['teamId']

    # Check cache first
    current_time = time.time()
    cached_account_data = account_data_cache.get(player_puuid)
    if cached_account_data and current_time - cached_account_data['timestamp'] < CACHE_EXPIRY_SECONDS:
        account_data = cached_account_data['data']
    else:
        # Fetch the gameName and tagLine using the puuid
        account_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/{player_puuid}"
        account_data = await fetch_data(session, account_url, headers)
        account_data_cache[player_puuid] = {'data': account_data, 'timestamp': current_time}

    if account_data:
        game_name = account_data.get('gameName', 'Unknown')
        tag_line = account_data.get('tagLine', '')
        summoner_name = f"{game_name}#{tag_line}" if tag_line else game_name
    else:
        summoner_name = "Unknown"

    rank = await get_player_rank(session, player_puuid, region, headers)
    champion_id = player['championId']
    champion_name = await fetch_champion_name(session, champion_id)

    player_data = {
        'summoner_name': summoner_name,
        'champion_name': champion_name,
        'rank': rank
    }

    return player_data, team_id

# Fetch player's rank based on PUUID
async def get_player_rank(session: aiohttp.ClientSession, puuid: str, region: str, headers: dict) -> str:
    # Fetch summoner data
    summoner_data = await fetch_summoner_data(session, puuid, region, headers)
    if not summoner_data:
        return "Unranked"

    summoner_id = summoner_data.get('id')
    league_data = await fetch_league_data(session, summoner_id, region, headers)
    if not league_data:
        return "Unranked"

    for entry in league_data:
        if entry['queueType'] == 'RANKED_SOLO_5x5':
            tier = entry.get('tier', 'Unranked').capitalize()
            rank = entry.get('rank', '').upper()
            lp = entry.get('leaguePoints', 0)
            return f"{tier} {rank} {lp} LP"
    return "Unranked"

# Fetch champion name by champion ID
async def fetch_champion_name(session: aiohttp.ClientSession, champion_id: int) -> str:
    # Fetch champion data from Data Dragon
    try:
        # Fetch champion data version
        versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        versions_data = await fetch_data(session, versions_url)
        latest_version = versions_data[0] if versions_data else '13.1.1'  # Default to some version

        # Fetch champion data
        champions_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json"
        champions_data = await fetch_data(session, champions_url)
        if champions_data and 'data' in champions_data:
            for champ_key, champ_info in champions_data['data'].items():
                if int(champ_info['key']) == champion_id:
                    return champ_info['name']
    except Exception as e:
        logging.error(f"Error fetching champion name: {e}")
    return "Unknown"

# Helper function to get emoji for a champion
async def get_emoji_for_champion(champion_name: str) -> str:
    global emojis
    if not emojis:
        emoji_data = await fetch_application_emojis()
        if emoji_data:
            for emoji in emoji_data:
                if isinstance(emoji, dict) and 'name' in emoji and 'id' in emoji:
                    normalized_name = emoji['name'].split('_')[0].lower()
                    emojis[normalized_name] = f"<:{emoji['name']}:{emoji['id']}>"
                else:
                    logging.error(f"Invalid emoji format detected: {emoji}")

    normalized_champion_name = SPECIAL_EMOJI_NAMES.get(champion_name, champion_name)
    return emojis.get(normalized_champion_name.lower(), "")

# Fetch all emojis for the bot
async def fetch_application_emojis():
    application_id = os.getenv('DISCORD_APP_ID')
    bot_token = os.getenv('TOKEN')

    if not application_id or not bot_token:
        logging.error("Missing DISCORD_APP_ID or TOKEN environment variables")
        return None

    url = f"https://discord.com/api/v10/applications/{application_id}/emojis"
    headers = {'Authorization': f'Bot {bot_token}'}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logging.error(f"Error fetching emojis: {response.status} - {response.reason}")
                return None
            data = await response.json()

            if isinstance(data, dict) and 'items' in data:
                data = data['items']
            elif not isinstance(data, list):
                logging.error("Unexpected emoji data format")
                return None

            valid_emojis = [emoji for emoji in data if isinstance(emoji, dict) and 'name' in emoji and 'id' in emoji]
            return valid_emojis if valid_emojis else None

# Function to set up the League command
async def setup(client: discord.Client):
    client.tree.add_command(league)

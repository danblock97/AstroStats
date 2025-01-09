import os
import time
import asyncio
import logging
import datetime
from typing import Literal
from collections import defaultdict

import aiohttp
import discord

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

REGIONS = Literal[
    "EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2",
    "JP1", "KR", "OC1", "SG2", "TW2", "VN2"
]

QUEUE_TYPE_NAMES = {
    "RANKED_SOLO_5x5": "Ranked Solo/Duo",
    "RANKED_FLEX_SR": "Ranked Flex 5v5",
    "CHERRY": "Arena"
}

last_fetch_times = defaultdict(lambda: datetime.datetime.min)
last_game_ids = defaultdict(lambda: None)
account_data_cache = {}
CACHE_EXPIRY_SECONDS = 300
emojis = {}

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
    "K'Sante": "KSante",
    "Kog'Maw": "KogMaw"
}

async def fetch_data(session: aiohttp.ClientSession, url: str, headers=None) -> dict:
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                logging.warning(f"Resource at {url} returned 404. Possibly not found.")
                return None
            elif response.status == 429:
                retry_after = int(response.headers.get('Retry-After', '1'))
                logging.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                await asyncio.sleep(retry_after)
                return await fetch_data(session, url, headers)
            else:
                logging.error(f"Error fetching data from {url}: {response.status} - {response.reason}")
                return None
    except Exception as e:
        logging.error(f"Exception during fetch_data: {e}")
        return None

async def fetch_summoner_data(session: aiohttp.ClientSession, puuid: str, region: str, headers: dict) -> dict:
    try:
        summoner_url = f"https://{region.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        data = await fetch_data(session, summoner_url, headers)
        if not data:
            logging.info(f"No summoner data found for PUUID {puuid} in region {region}.")
        return data
    except Exception as e:
        logging.error(f"Failed to fetch summoner data: {e}")
        return None

async def fetch_league_data(session: aiohttp.ClientSession, summoner_id: str, region: str, headers: dict) -> dict:
    try:
        league_url = f"https://{region.lower()}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        data = await fetch_data(session, league_url, headers)
        if not data:
            logging.info(f"No league data found for summoner ID {summoner_id} in region {region}.")
        return data
    except Exception as e:
        logging.error(f"Failed to fetch league data: {e}")
        return None

async def fetch_live_game(session: aiohttp.ClientSession, puuid: str, region: str, headers: dict) -> dict:
    try:
        live_game_url = f"https://{region.lower()}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        data = await fetch_data(session, live_game_url, headers)
        if not data:
            logging.info(f"No live game data found for PUUID {puuid} in region {region}.")
        return data
    except Exception as e:
        logging.error(f"Failed to fetch live game data: {e}")
        return None

async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=(
            f"{description}\n\nFor more assistance, visit "
            "[AstroStats Support](https://astrostats.vercel.app)"
        ),
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    await interaction.followup.send(embed=embed)

@discord.app_commands.command(name="league", description="Check your League of Legends Player Stats")
async def league(interaction: discord.Interaction, region: REGIONS, riotid: str):
    try:
        await interaction.response.defer()
        if "#" not in riotid:
            logging.info("User provided Riot ID without '#' separator.")
            await send_error_embed(
                interaction,
                "Invalid Riot ID",
                "Please enter your Riot ID in the format gameName#tagLine."
            )
            return

        game_name, tag_line = riotid.split("#")
        riot_api_key = os.getenv('LOL_API')
        if not riot_api_key:
            logging.error("Riot API key is missing in environment variables.")
            await send_error_embed(
                interaction,
                "Configuration Error",
                "Riot API key is not configured. Please contact the bot owner."
            )
            return
        headers = {'X-Riot-Token': riot_api_key}

        regional_url = (
            "https://europe.api.riotgames.com/"
            f"riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        )
        async with aiohttp.ClientSession() as session:
            account_data = await fetch_data(session, regional_url, headers)
            puuid = account_data.get('puuid') if account_data else None

            if not puuid:
                logging.info(f"Failed to retrieve PUUID for {riotid}. Possibly invalid or no account found.")
                await send_error_embed(
                    interaction,
                    "Account Not Found",
                    (
                        f"Failed to retrieve PUUID for {riotid}. Make sure the gameName#tagLine is correct. "
                        "You may need to double-check your Riot ID or try another region."
                    )
                )
                return

            summoner_data = await fetch_summoner_data(session, puuid, region, headers)
            if not summoner_data:
                logging.info(f"Summoner data not found for PUUID {puuid} in region {region}.")
                await send_error_embed(
                    interaction,
                    "No Data Found",
                    (
                        f"No Summoner data found in region '{region}' for the Riot ID {riotid}. "
                        "Verify that this account exists in the selected region, "
                        "or re-search with a different region."
                    )
                )
                return

            league_data = await fetch_league_data(session, summoner_data['id'], region, headers)
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

            if league_data:
                for league_info in league_data:
                    queue_type = QUEUE_TYPE_NAMES.get(league_info['queueType'], "Other")
                    tier = league_info.get('tier', 'Unranked').capitalize()
                    rank = league_info.get('rank', '').upper()
                    lp = league_info.get('leaguePoints', 0)
                    wins = league_info.get('wins', 0)
                    losses = league_info.get('losses', 0)
                    total_games = wins + losses
                    winrate = int((wins / total_games) * 100) if total_games > 0 else 0

                    rank_data = (
                        f"{tier} {rank} {lp} LP\n"
                        f"Wins: {wins}\n"
                        f"Losses: {losses}\n"
                        f"Winrate: {winrate}%"
                    )
                    embed.add_field(name=queue_type, value=rank_data, inline=True)
            else:
                embed.add_field(name="Rank", value="Unranked", inline=False)

            embed.add_field(
                name="Support Us ❤️",
                value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)",
                inline=False
            )
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.set_footer(text="Built By Goldiez ❤️ Visit clutchgg.lol for more!")

            view = create_live_game_view(
                interaction.client, embed, puuid, region,
                headers, game_name, tag_line
            )
            await interaction.followup.send(embed=embed, view=view)

    except aiohttp.ClientError as e:
        logging.error(f"Request Error: {e}")
        await send_error_embed(
            interaction,
            "API Error",
            "Sorry, I couldn't retrieve League of Legends stats at the moment. Please try again later."
        )
    except (KeyError, ValueError) as e:
        logging.error(f"Data Error: {e}")
        await send_error_embed(
            interaction,
            "Data Error",
            (
                "Failed to retrieve summoner data due to unexpected data format. "
                "Please ensure your Riot ID is correct and try again."
            )
        )
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        await send_error_embed(
            interaction,
            "Unexpected Error",
            (
                "An unexpected error occurred while processing your request. "
                "Please try again later or contact support if the issue persists."
            )
        )

def create_live_game_view(client, embed, puuid, region, headers, game_name, tag_line):
    view = discord.ui.View()
    live_game_button = discord.ui.Button(label="Live Game", style=discord.ButtonStyle.primary)

    async def live_game_callback(interaction: discord.Interaction):
        try:
            live_game_button.label = "Fetching..."
            live_game_button.disabled = True
            await interaction.response.edit_message(view=view)

            async with aiohttp.ClientSession() as session:
                await update_live_game_view(
                    interaction, embed, puuid, region, headers,
                    live_game_button, game_name, tag_line, view, session
                )
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching live game data: {e}")
            await send_error_embed(
                interaction,
                "Live Game Error",
                "Unable to fetch live game data. Please check again or try re-searching your account."
            )
        except Exception as e:
            logging.error(f"Unexpected Error in live_game_callback: {e}")
            await send_error_embed(
                interaction,
                "Live Game Error",
                "An unexpected error occurred while trying to fetch the live game."
            )
        finally:
            live_game_button.disabled = False
            live_game_button.label = "Live Game"
            await interaction.edit_original_response(view=view)

    live_game_button.callback = live_game_callback
    view.add_item(live_game_button)
    return view

async def update_live_game_view(
    interaction: discord.Interaction,
    embed: discord.Embed,
    puuid: str,
    region: str,
    headers: dict,
    live_game_button: discord.ui.Button,
    game_name: str,
    tag_line: str,
    view: discord.ui.View,
    session: aiohttp.ClientSession
):
    live_game_data = await fetch_live_game(session, puuid, region, headers)
    if not live_game_data or 'status' in live_game_data:
        logging.info("No live game found or error in live game data response.")
        no_game_embed = discord.Embed(
            title="No Live Game Found",
            description=(
                "It seems you're not in a live game. Make sure you're in champion select or loading. "
                "Try searching again if you believe you should have a live match. "
                "You may also need to re-run the /league command if your account data is stale."
            ),
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        await interaction.followup.send(embed=no_game_embed)
        return

    game_id = live_game_data['gameId']
    if last_game_ids[puuid] == game_id:
        logging.info("User attempted to fetch the same live game data again.")
        await interaction.followup.send(
            "No new game data since the last fetch. You may still be in the same game.",
            ephemeral=True
        )
    else:
        last_game_ids[puuid] = game_id
        await process_game_data(interaction, embed, live_game_data, puuid, region, headers, session)

    last_fetch_times[puuid] = datetime.datetime.utcnow()

async def process_game_data(
    interaction: discord.Interaction,
    embed: discord.Embed,
    live_game_data: dict,
    puuid: str,
    region: str,
    headers: dict,
    session: aiohttp.ClientSession
):
    blue_team = []
    red_team = []
    tasks = []
    for player in live_game_data['participants']:
        tasks.append(fetch_participant_data(player, region, headers, session))

    participants_data = await asyncio.gather(*tasks)
    for player_data, team_id in participants_data:
        if team_id == 100:
            blue_team.append(player_data)
        else:
            red_team.append(player_data)

    embed.clear_fields()
    embed.title = f"Live Game Info (ID: {live_game_data['gameId']})"

    blue_team_champions = '\n'.join([
        f"{await get_emoji_for_champion(p['champion_name'])} {p['champion_name']}" for p in blue_team
    ])
    blue_team_names = '\n'.join([p['summoner_name'] for p in blue_team])
    blue_team_ranks = '\n'.join([p['rank'] for p in blue_team])

    red_team_champions = '\n'.join([
        f"{await get_emoji_for_champion(p['champion_name'])} {p['champion_name']}" for p in red_team
    ])
    red_team_names = '\n'.join([p['summoner_name'] for p in red_team])
    red_team_ranks = '\n'.join([p['rank'] for p in red_team])

    embed.add_field(name="Blue Team", value=blue_team_champions or "No data", inline=True)
    embed.add_field(name="Summoner Names", value=blue_team_names or "No data", inline=True)
    embed.add_field(name="Rank", value=blue_team_ranks or "No data", inline=True)

    embed.add_field(name="Red Team", value=red_team_champions or "No data", inline=True)
    embed.add_field(name="Summoner Names", value=red_team_names or "No data", inline=True)
    embed.add_field(name="Rank", value=red_team_ranks or "No data", inline=True)

    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text="Live Game Data - Provided by AstroStats")
    await interaction.followup.send(embed=embed)

async def fetch_participant_data(player, region, headers, session):
    try:
        player_puuid = player['puuid']
        team_id = player['teamId']
        current_time = time.time()
        cached_account_data = account_data_cache.get(player_puuid)

        if cached_account_data and current_time - cached_account_data['timestamp'] < CACHE_EXPIRY_SECONDS:
            account_data = cached_account_data['data']
        else:
            account_url = (
                "https://europe.api.riotgames.com/riot/account/v1/"
                f"accounts/by-puuid/{player_puuid}"
            )
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

        return {'summoner_name': summoner_name, 'champion_name': champion_name, 'rank': rank}, team_id
    except Exception as e:
        logging.error(f"Error fetching participant data: {e}")
        return {'summoner_name': 'Unknown', 'champion_name': 'Unknown', 'rank': 'Unranked'}, player['teamId']

async def get_player_rank(session: aiohttp.ClientSession, puuid: str, region: str, headers: dict) -> str:
    try:
        summoner_data = await fetch_summoner_data(session, puuid, region, headers)
        if not summoner_data:
            logging.info(f"No summoner data returned when attempting to get rank for PUUID {puuid}.")
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
    except Exception as e:
        logging.error(f"Error getting player rank: {e}")
        return "Unranked"

async def fetch_champion_name(session: aiohttp.ClientSession, champion_id: int) -> str:
    try:
        versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        versions_data = await fetch_data(session, versions_url)
        latest_version = versions_data[0] if versions_data else '13.1.1'

        champions_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json"
        champions_data = await fetch_data(session, champions_url)
        if champions_data and 'data' in champions_data:
            for champ_key, champ_info in champions_data['data'].items():
                if int(champ_info['key']) == champion_id:
                    return champ_info['name']
    except Exception as e:
        logging.error(f"Error fetching champion name for ID {champion_id}: {e}")
    return "Unknown"

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

async def fetch_application_emojis():
    application_id = os.getenv('DISCORD_APP_ID')
    bot_token = os.getenv('TOKEN')
    if not application_id or not bot_token:
        logging.error("Missing DISCORD_APP_ID or TOKEN environment variables.")
        return None

    url = f"https://discord.com/api/v10/applications/{application_id}/emojis"
    headers = {'Authorization': f'Bot {bot_token}'}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Error fetching emojis: {response.status} - {response.reason}")
                    return None
                data = await response.json()
                if isinstance(data, dict) and 'items' in data:
                    data = data['items']
                elif not isinstance(data, list):
                    logging.error("Unexpected emoji data format.")
                    return None
                valid_emojis = [
                    emoji for emoji in data
                    if isinstance(emoji, dict) and 'name' in emoji and 'id' in emoji
                ]
                return valid_emojis if valid_emojis else None
    except Exception as e:
        logging.error(f"Exception fetching emojis: {e}")
        return None

async def setup(client: discord.Client):
    client.tree.add_command(league)

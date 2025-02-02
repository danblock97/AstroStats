import os
import time
import asyncio
import logging
import datetime
from typing import Literal
from collections import defaultdict

import aiohttp
import discord
from discord.ext import commands

from utils.embeds import get_conditional_embed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REGIONS = Literal[
    "EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2",
    "JP1", "KR", "OC1", "SG2", "TW2", "VN2"
]

QUEUE_TYPE_NAMES = {
    "RANKED_SOLO_5x5": "Ranked Solo/Duo",
    "RANKED_FLEX_SR": "Ranked Flex 5v5",
    "CHERRY": "Arena"
}

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
    "Kog'Maw": "KogMaw",
    "Twisted Fate": "TwistedFate",
    "Dr. Mundo": "DrMundo",
    "Rek'Sai": "RekSai",
    "Kai'Sa": "KaiSa",
    "Vel'Koz": "Velkoz",
    "Kha'Zix": "Khazix",
}


async def fetch_data(session: aiohttp.ClientSession, url: str, headers=None) -> dict:
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return None
            elif response.status == 429:
                retry_after = int(response.headers.get('Retry-After', '1'))
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
            return None
        return data
    except Exception as e:
        logging.error(f"Failed to fetch summoner data: {e}")
        return None


async def fetch_league_data(session: aiohttp.ClientSession, summoner_id: str, region: str, headers: dict) -> dict:
    try:
        league_url = f"https://{region.lower()}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        data = await fetch_data(session, league_url, headers)
        if not data:
            return None
        return data
    except Exception as e:
        logging.error(f"Failed to fetch league data: {e}")
        return None


async def fetch_live_game(session: aiohttp.ClientSession, puuid: str, region: str, headers: dict) -> dict:
    try:
        live_game_url = f"https://{region.lower()}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        data = await fetch_data(session, live_game_url, headers)
        if not data:
            return None
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


async def add_live_game_data_to_embed(embed: discord.Embed, live_game_data: dict, region: str, headers: dict, session: aiohttp.ClientSession):
    """
    Processes live game data and appends live game information to the provided embed.
    """
    try:
        tasks = []
        for player in live_game_data.get('participants', []):
            tasks.append(fetch_participant_data(player, region, headers, session))
    
        participants_data = await asyncio.gather(*tasks)
        blue_team = []
        red_team = []
        for player_data, team_id in participants_data:
            if team_id == 100:
                blue_team.append(player_data)
            else:
                red_team.append(player_data)
    
        # Add a divider field for Live Game Info
        embed.add_field(name="\u200b", value="**Currently In Game**", inline=False)
    
        # Display the game mode (or queue configuration)
        queue_config_id = live_game_data.get("gameQueueConfigId")
        if queue_config_id:
            game_mode_name = {
                420: "Ranked Solo/Duo",
                440: "Ranked Flex 5v5",
                450: "ARAM",
            }.get(queue_config_id, f"Queue ID {queue_config_id}")
        else:
            game_mode_name = live_game_data.get("gameMode", "Unknown")
        embed.add_field(name="Game Mode", value=game_mode_name, inline=False)
    
        blue_team_champions = '\n'.join([
            f"{await get_emoji_for_champion(p['champion_name'])} {p['champion_name']}" for p in blue_team
        ]) or "No data"
        blue_team_names = '\n'.join([p['summoner_name'] for p in blue_team]) or "No data"
        blue_team_ranks = '\n'.join([p['rank'] for p in blue_team]) or "No data"
    
        red_team_champions = '\n'.join([
            f"{await get_emoji_for_champion(p['champion_name'])} {p['champion_name']}" for p in red_team
        ]) or "No data"
        red_team_names = '\n'.join([p['summoner_name'] for p in red_team]) or "No data"
        red_team_ranks = '\n'.join([p['rank'] for p in red_team]) or "No data"
    
        embed.add_field(name="Blue Team Champions", value=blue_team_champions, inline=True)
        embed.add_field(name="Blue Team Names", value=blue_team_names, inline=True)
        embed.add_field(name="Blue Team Ranks", value=blue_team_ranks, inline=True)
    
        embed.add_field(name="Red Team Champions", value=red_team_champions, inline=True)
        embed.add_field(name="Red Team Names", value=red_team_names, inline=True)
        embed.add_field(name="Red Team Ranks", value=red_team_ranks, inline=True)
    except Exception as e:
        logging.error(f"Error adding live game data to embed: {e}")


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
        return {'summoner_name': 'Unknown', 'champion_name': 'Unknown', 'rank': 'Unranked'}, player.get('teamId', 0)


async def get_player_rank(session: aiohttp.ClientSession, puuid: str, region: str, headers: dict) -> str:
    try:
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


class League(commands.GroupCog, group_name="league"):
    """A cog grouping League of Legends commands under `/league`."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="profile", description="Check your League of Legends Player Stats")
    async def profile(self, interaction: discord.Interaction, region: REGIONS, riotid: str):
        try:
            await interaction.response.defer()
            if "#" not in riotid:
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
                    color=0x1a78ae,
                    url=f"https://www.clutchgg.lol/profile?gameName={game_name}&tagLine={tag_line}&region={region}"
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
    
                # Check for live game data and add it if available.
                live_game_data = await fetch_live_game(session, puuid, region, headers)
                if live_game_data and 'status' not in live_game_data:
                    await add_live_game_data_to_embed(embed, live_game_data, region, headers, session)
    
                embed.add_field(
                    name="Support Us ❤️",
                    value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)",
                    inline=False
                )
                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                embed.set_footer(text="Built By Goldiez ❤️ Visit clutchgg.lol for more!")
    
                conditional_embed = await get_conditional_embed(interaction, 'LEAGUE_EMBED', discord.Color.orange())
                embeds = [embed]
                if conditional_embed:
                    embeds.append(conditional_embed)
    
                await interaction.followup.send(embeds=embeds)
    
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
    
    @discord.app_commands.command(name="championmastery", description="Show your top 10 Champion Masteries")
    async def championmastery(self, interaction: discord.Interaction, region: REGIONS, riotid: str):
        try:
            await interaction.response.defer()
            if "#" not in riotid:
                await send_error_embed(
                    interaction,
                    "Invalid Riot ID",
                    "Please enter your Riot ID in the format gameName#tagLine."
                )
                return
    
            game_name, tag_line = riotid.split("#")
            riot_api_key = os.getenv("LOL_API")
            if not riot_api_key:
                logging.error("Riot API key is missing in environment variables.")
                await send_error_embed(
                    interaction,
                    "Configuration Error",
                    "Riot API key is not configured. Please contact the bot owner."
                )
                return
            headers = {'X-Riot-Token': riot_api_key}
    
            # Retrieve the PUUID using the global account endpoint.
            account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
            async with aiohttp.ClientSession() as session:
                account_data = await fetch_data(session, account_url, headers)
                puuid = account_data.get("puuid") if account_data else None
                if not puuid:
                    await send_error_embed(
                        interaction,
                        "Account Not Found",
                        f"Failed to retrieve PUUID for {riotid}. Make sure your Riot ID is correct."
                    )
                    return
    
                # Fetch champion mastery data.
                mastery_url = f"https://{region.lower()}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
                mastery_data = await fetch_data(session, mastery_url, headers)
                if mastery_data is None:
                    await send_error_embed(
                        interaction,
                        "Error",
                        "Failed to fetch champion mastery data. Please try again later."
                    )
                    return
    
                # Get the top 10 champion mastery entries.
                top_masteries = mastery_data[:10]
    
                embed = discord.Embed(
                    title=f"Champion Mastery for {riotid}",
                    color=0x1a78ae,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                description_lines = []
                for mastery in top_masteries:
                    champion_id = mastery.get("championId")
                    champion_name = await fetch_champion_name(session, champion_id)
                    emoji = await get_emoji_for_champion(champion_name)
                    mastery_level = mastery.get("championLevel", "N/A")
                    mastery_points = mastery.get("championPoints", "N/A")
                    description_lines.append(f"{emoji} **{champion_name}** - Level {mastery_level} - {mastery_points} pts")
                embed.description = "\n".join(description_lines)
                embed.set_footer(text="Built By Goldiez ❤️ Visit clutchgg.lol for more!")
                await interaction.followup.send(embed=embed)
    
        except aiohttp.ClientError as e:
            logging.error(f"Request Error: {e}")
            await send_error_embed(
                interaction,
                "API Error",
                "Could not retrieve champion mastery data. Please try again later."
            )
        except Exception as e:
            logging.error(f"Unexpected Error: {e}")
            await send_error_embed(
                interaction,
                "Unexpected Error",
                "An unexpected error occurred while processing your request."
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(League(bot))

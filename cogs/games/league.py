import os
import time
import asyncio
import logging
import datetime
from typing import Literal, Dict, Any, List, Optional
from collections import defaultdict
from urllib.parse import urlencode

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

from config.settings import LOL_API, DISCORD_APP_ID, TOKEN
from config.constants import LEAGUE_REGIONS, LEAGUE_QUEUE_TYPE_NAMES, SPECIAL_EMOJI_NAMES
from core.errors import send_error_embed
from core.utils import get_conditional_embed

logger = logging.getLogger(__name__)

account_data_cache = {}
CACHE_EXPIRY_SECONDS = 300


class LeagueCog(commands.GroupCog, group_name="league"):
    """A cog grouping League of Legends commands under `/league`."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.emojis = {}  # Local emoji cache for the cog
        self.bot.loop.create_task(self.initialize_emojis())
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    async def initialize_emojis(self):
        """Initialize emoji data when the cog is loaded."""
        try:
            emoji_data = await self.fetch_application_emojis()
            if emoji_data:
                for e in emoji_data:
                    if isinstance(e, dict) and 'name' in e and 'id' in e:
                        self.emojis[e['name'].lower()] = f"<:{e['name']}:{e['id']}>"
                    else:
                        logger.warning(f"Invalid emoji format: {e}")
                logger.info(f"Loaded {len(self.emojis)} emojis")
            else:
                logger.warning("No emojis found or emoji fetching failed")
        except Exception as e:
            logger.error(f"Error initializing emojis: {e}")
            # Continue without emojis - don't raise exception

    @app_commands.command(name="profile", description="Check your League of Legends Player Stats")
    async def profile(self, interaction: discord.Interaction, region: Literal[
        "EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2", "JP1", "KR", "OC1", "SG2", "TW2", "VN2"], riotid: str):
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
            riot_api_key = LOL_API
            if not riot_api_key:
                logger.error("Riot API key is missing in environment variables.")
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
                account_data = await self.fetch_data(session, regional_url, headers)
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

                summoner_data = await self.fetch_summoner_data(session, puuid, region, headers)
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

                league_data = await self.fetch_league_data(session, summoner_data['id'], region, headers)
                query_params = urlencode({
                    "gameName": game_name,
                    "tagLine": tag_line,
                    "region": region
                })
                profile_url = f"https://www.clutchgg.lol/league/profile?{query_params}"

                embed = discord.Embed(
                    title=f"{game_name}#{tag_line} - Level {summoner_data['summonerLevel']}",
                    color=0x1a78ae,
                    url=profile_url
                )
                embed.set_thumbnail(
                    url=(
                        "https://raw.communitydragon.org/latest/game/assets/ux/summonericons/"
                        f"profileicon{summoner_data['profileIconId']}.png"
                    )
                )

                # Prepare default values for the required queues
                ranked_info = {
                    "Ranked Solo/Duo": "Unranked",
                    "Ranked Flex 5v5": "Unranked"
                }

                if league_data:
                    for league_info in league_data:
                        if league_info.get('queueType') in ["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]:
                            queue_type = LEAGUE_QUEUE_TYPE_NAMES.get(league_info['queueType'], "Other")
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
                            ranked_info[queue_type] = rank_data

                # Always add two fields for Ranked Solo/Duo and Ranked Flex 5v5 in that order
                embed.add_field(name="Ranked Solo/Duo", value=ranked_info["Ranked Solo/Duo"], inline=True)
                embed.add_field(name="Ranked Flex 5v5", value=ranked_info["Ranked Flex 5v5"], inline=True)

                # Check for live game data and add it if available.
                live_game_data = await self.fetch_live_game(session, puuid, region, headers)
                if live_game_data and 'status' not in live_game_data:
                    await self.add_live_game_data_to_embed(embed, live_game_data, region, headers, session)

                embed.add_field(
                    name="Support Us ❤️",
                    value="[If you enjoy using this bot, consider supporting us!](https://astrostats.info)",
                    inline=False
                )
                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")

                conditional_embed = await get_conditional_embed(interaction, 'LEAGUE_EMBED', discord.Color.orange())
                embeds = [embed]
                if conditional_embed:
                    embeds.append(conditional_embed)

                await interaction.followup.send(embeds=embeds)

        except aiohttp.ClientError as e:
            logger.error(f"Request Error: {e}")
            await send_error_embed(
                interaction,
                "API Error",
                "Sorry, I couldn't retrieve League of Legends stats at the moment. Please try again later."
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Data Error: {e}")
            await send_error_embed(
                interaction,
                "Data Error",
                (
                    "Failed to retrieve summoner data due to unexpected data format. "
                    "Please ensure your Riot ID is correct and try again."
                )
            )
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            await send_error_embed(
                interaction,
                "Unexpected Error",
                (
                    "An unexpected error occurred while processing your request. "
                    "Please try again later or contact support if the issue persists."
                )
            )

    @app_commands.command(name="championmastery", description="Show your top 10 Champion Masteries")
    async def championmastery(self, interaction: discord.Interaction, region: Literal[
        "EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2", "JP1", "KR", "OC1", "SG2", "TW2", "VN2"], riotid: str):
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
            riot_api_key = LOL_API
            if not riot_api_key:
                logger.error("Riot API key is missing in environment variables.")
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
                account_data = await self.fetch_data(session, account_url, headers)
                puuid = account_data.get("puuid") if account_data else None
                if not puuid:
                    await send_error_embed(
                        interaction,
                        "Account Not Found",
                        f"Failed to retrieve PUUID for {riotid}. Make sure your Riot ID is correct."
                    )
                    return

                # Get summoner ID from puuid
                summoner_data = await self.fetch_summoner_data(session, puuid, region, headers)
                if not summoner_data:
                    await send_error_embed(
                        interaction,
                        "No Data Found",
                        f"No summoner data found in region '{region}' for {riotid}."
                    )
                    return

                # Fetch champion mastery data.
                mastery_url = f"https://{region.lower()}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
                mastery_data = await self.fetch_data(session, mastery_url, headers)
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
                    champion_name = await self.fetch_champion_name(session, champion_id)
                    emoji = await self.get_emoji_for_champion(champion_name)
                    mastery_level = mastery.get("championLevel", "N/A")
                    mastery_points = mastery.get("championPoints", "N/A")

                    # If mastery_points is a number, format it with commas
                    if mastery_points != "N/A":
                        mastery_points = f"{mastery_points:,}"

                    description_lines.append(
                        f"{emoji} **{champion_name}: Mastery {mastery_level} - {mastery_points} pts**"
                    )

                embed.description = "\n".join(description_lines)
                embed.add_field(
                    name="Support Us ❤️",
                    value="[If you enjoy using this bot, consider supporting us!](https://astrostats.info)",
                    inline=False
                )
                embed.set_footer(text="Built By Goldiez ❤️ Visit clutchgg.lol for more!")
                await interaction.followup.send(embed=embed)

        except aiohttp.ClientError as e:
            logger.error(f"Request Error: {e}")
            await send_error_embed(
                interaction,
                "API Error",
                "Could not retrieve champion mastery data. Please try again later."
            )
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            await send_error_embed(
                interaction,
                "Unexpected Error",
                "An unexpected error occurred while processing your request."
            )

    # Helper methods
    async def fetch_data(self, session: aiohttp.ClientSession, url: str, headers=None) -> dict:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None
                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', '1'))
                    await asyncio.sleep(retry_after)
                    return await self.fetch_data(session, url, headers)
                else:
                    logger.error(f"Error fetching data from {url}: {response.status} - {response.reason}")
                    return None
        except Exception as e:
            logger.error(f"Exception during fetch_data: {e}")
            return None

    async def fetch_summoner_data(self, session: aiohttp.ClientSession, puuid: str, region: str, headers: dict) -> dict:
        try:
            summoner_url = f"https://{region.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            data = await self.fetch_data(session, summoner_url, headers)
            if not data:
                return None
            return data
        except Exception as e:
            logger.error(f"Failed to fetch summoner data: {e}")
            return None

    async def fetch_league_data(self, session: aiohttp.ClientSession, summoner_id: str, region: str,
                                headers: dict) -> dict:
        try:
            league_url = f"https://{region.lower()}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
            data = await self.fetch_data(session, league_url, headers)
            if not data:
                return None
            return data
        except Exception as e:
            logger.error(f"Failed to fetch league data: {e}")
            return None

    async def fetch_live_game(self, session: aiohttp.ClientSession, puuid: str, region: str,
                              headers: dict) -> dict:
        try:
            live_game_url = f"https://{region.lower()}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
            data = await self.fetch_data(session, live_game_url, headers)
            if not data:
                return None
            return data
        except Exception as e:
            logger.error(f"Failed to fetch live game data: {e}")
            return None

    async def add_live_game_data_to_embed(self, embed: discord.Embed, live_game_data: dict, region: str, headers: dict,
                                          session: aiohttp.ClientSession):
        """
        Processes live game data and appends live game information to the provided embed.
        Special handling is added for Arena mode (queueId 1700) where the game is split into 8 teams of 2.
        """
        try:
            tasks = []
            for player in live_game_data.get('participants', []):
                tasks.append(self.fetch_participant_data(player, region, headers, session))
            participants_data = await asyncio.gather(*tasks)

            # Determine game mode based on queue id.
            queue_config_id = live_game_data.get("gameQueueConfigId")
            if queue_config_id == 1700 or queue_config_id == 1710:
                game_mode_name = "Arena"
                embed.add_field(name="\u200b", value=f"**Currently In Game - {game_mode_name}**", inline=False)
                # Extract player data from participants_data (ignoring any team_id, since Arena teams are implicit)
                arena_players = [p for p, _ in participants_data]
                # Split the 16 players into 8 teams of 2
                for i in range(0, len(arena_players), 2):
                    team = arena_players[i:i + 2]
                    team_details = "\n".join([
                        f"{await self.get_emoji_for_champion(p['champion_name'])} {p['champion_name']} - {p['riotId']} ({p['rank']})"
                        for p in team
                    ])
                    embed.add_field(name=f"Team {i // 2 + 1}", value=team_details, inline=True)
            else:
                # Non-Arena modes – keep the current two-team (blue/red) layout.
                if queue_config_id:
                    game_mode_name = {
                        400: "Normal Draft",
                        420: "Ranked Solo/Duo",
                        440: "Ranked Flex 5v5",
                        450: "ARAM",
                        700: "Clash",
                        830: "Co-op vs. AI Intro",
                        840: "Co-op vs. AI Beginner",
                        850: "Co-op vs. AI Intermediate",
                        900: "URF",
                    }.get(queue_config_id, f"Queue ID {queue_config_id}")
                else:
                    game_mode_name = live_game_data.get("gameMode", "Unknown")
                embed.add_field(name="\u200b", value=f"**Currently In Game - {game_mode_name}**", inline=False)

                blue_team = []
                red_team = []
                for player_data, team_id in participants_data:
                    if team_id == 100:
                        blue_team.append(player_data)
                    else:
                        red_team.append(player_data)

                blue_team_champions = '\n'.join([
                    f"{await self.get_emoji_for_champion(p['champion_name'])} {p['champion_name']}" for p in blue_team
                ]) or "No data"
                blue_team_names = '\n'.join([p['riotId'] for p in blue_team]) or "No data"
                blue_team_ranks = '\n'.join([p['rank'] for p in blue_team]) or "No data"

                red_team_champions = '\n'.join([
                    f"{await self.get_emoji_for_champion(p['champion_name'])} {p['champion_name']}" for p in red_team
                ]) or "No data"
                red_team_names = '\n'.join([p['riotId'] for p in red_team]) or "No data"
                red_team_ranks = '\n'.join([p['rank'] for p in red_team]) or "No data"

                embed.add_field(name="Blue Team", value=blue_team_champions, inline=True)
                embed.add_field(name="RiotID", value=blue_team_names, inline=True)
                embed.add_field(name="Rank", value=blue_team_ranks, inline=True)

                embed.add_field(name="Red Team", value=red_team_champions, inline=True)
                embed.add_field(name="RiotID", value=red_team_names, inline=True)
                embed.add_field(name="Rank", value=red_team_ranks, inline=True)
        except Exception as e:
            logger.error(f"Error adding live game data to embed: {e}")

    async def fetch_participant_data(self, player, region, headers, session):
        try:
            summoner_id = player['summonerId']
            team_id = player['teamId']
            current_time = time.time()
            cached_account_data = account_data_cache.get(summoner_id)

            if cached_account_data and current_time - cached_account_data['timestamp'] < CACHE_EXPIRY_SECONDS:
                account_data = cached_account_data['data']
            else:
                account_url = f"https://{region.lower()}.api.riotgames.com/lol/summoner/v4/summoner/{summoner_id}"
                summoner_data = await self.fetch_data(session, account_url, headers)

                if summoner_data and 'puuid' in summoner_data:
                    riot_id_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-puuid/{summoner_data['puuid']}"
                    account_data = await self.fetch_data(session, riot_id_url, headers)
                    if account_data:
                        account_data_cache[summoner_id] = {'data': account_data, 'timestamp': current_time}
                else:
                    account_data = None

            if account_data:
                game_name = account_data.get('gameName', 'Unknown')
                tag_line = account_data.get('tagLine', '')
                riotId = f"{game_name}#{tag_line}" if tag_line else game_name
            else:
                # Try riotId first, then summonerName, finally default to 'Unknown'
                riotId = player.get('riotId') or player.get('summonerName', 'Unknown')

            rank = await self.get_player_rank(session, summoner_id, region, headers)
            champion_id = player['championId']
            champion_name = await self.fetch_champion_name(session, champion_id)

            return {'riotId': riotId, 'champion_name': champion_name, 'rank': rank}, team_id
        except Exception as e:
            logger.error(f"Error fetching participant data: {e}")
            return {'riotId': 'Unknown', 'champion_name': 'Unknown', 'rank': 'Unranked'}, player.get('teamId', 0)

    async def get_player_rank(self, session: aiohttp.ClientSession, summoner_id: str, region: str,
                              headers: dict) -> str:
        try:
            league_data = await self.fetch_league_data(session, summoner_id, region, headers)
            if not isinstance(league_data, list):
                return "Unranked"

            for entry in league_data:
                if isinstance(entry, dict) and entry.get('queueType') == 'RANKED_SOLO_5x5':
                    tier = entry.get('tier') or "Unranked"
                    if isinstance(tier, str):
                        tier = tier.capitalize()
                    else:
                        tier = "Unranked"
                    rank = entry.get('rank', '').upper()
                    lp = entry.get('leaguePoints', 0)
                    return f"{tier} {rank} {lp} LP"
            return "Unranked"
        except Exception as e:
            logger.error(f"Error getting player rank: {e}")
            return "Unranked"

    async def fetch_champion_name(self, session: aiohttp.ClientSession, champion_id: int) -> str:
        try:
            versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
            versions_data = await self.fetch_data(session, versions_url)
            latest_version = versions_data[0] if versions_data else '13.1.1'

            champions_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json"
            champions_data = await self.fetch_data(session, champions_url)
            if champions_data and 'data' in champions_data:
                for champ_key, champ_info in champions_data['data'].items():
                    if int(champ_info['key']) == champion_id:
                        return champ_info['name']
        except Exception as e:
            logger.error(f"Error fetching champion name for ID {champion_id}: {e}")
        return "Unknown"

    async def get_emoji_for_champion(self, champion_name: str) -> str:
        """Get the emoji for a champion name."""
        try:
            normalized_champion_name = SPECIAL_EMOJI_NAMES.get(champion_name, champion_name)
            return self.emojis.get(normalized_champion_name.lower(), "")
        except Exception as e:
            logger.error(f"Error getting emoji for champion {champion_name}: {e}")
            return ""  # Return empty string on any error

    async def fetch_application_emojis(self):
        """Fetch emojis from the Discord application."""
        try:
            application_id = DISCORD_APP_ID
            bot_token = TOKEN
            if not application_id or not bot_token:
                logger.warning("Missing DISCORD_APP_ID or TOKEN environment variables.")
                return None

            url = f"https://discord.com/api/v10/applications/{application_id}/emojis"
            headers = {'Authorization': f'Bot {bot_token}'}

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            logger.error(f"Error fetching emojis: {response.status} - {response.reason}")
                            return None
                        data = await response.json()
                        if isinstance(data, dict) and 'items' in data:
                            data = data['items']
                        elif not isinstance(data, list):
                            logger.error("Unexpected emoji data format.")
                            return None
                        valid_emojis = [
                            emoji for emoji in data
                            if isinstance(emoji, dict) and 'name' in emoji and 'id' in emoji
                        ]
                        return valid_emojis if valid_emojis else None
                except aiohttp.ClientError as e:
                    logger.error(f"Client error fetching emojis: {e}")
                    return None
        except Exception as e:
            logger.error(f"Exception fetching emojis: {e}")
            return None


async def setup(bot: commands.Bot):
    await bot.add_cog(LeagueCog(bot))

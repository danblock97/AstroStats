import os
import time
import asyncio
import logging
import datetime
import re
from typing import Literal, Dict, Any, List, Optional
from collections import defaultdict
from urllib.parse import urlencode

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

from config.settings import LOL_API, DISCORD_APP_ID, TOKEN
from config.constants import LEAGUE_REGIONS, LEAGUE_QUEUE_TYPE_NAMES, SPECIAL_EMOJI_NAMES, REGION_TO_ROUTING
from core.errors import send_error_embed
from core.utils import get_conditional_embed
from ui.embeds import get_premium_promotion_view
from discord.ui import View, Button

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
                logger.debug(f"Loaded {len(self.emojis)} emojis into cache.") # Reduced verbosity
                if not self.emojis:
                    logger.warning("Emoji data was fetched, but the cache is still empty. Check data format.") # Added log
            else:
                logger.warning("No emojis found or emoji fetching failed. Emoji cache is empty.") # Modified log
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

                league_data = await self.fetch_league_data(session, puuid, region, headers)
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
                profile_icon_id = summoner_data.get('profileIconId')
                if profile_icon_id is not None and isinstance(profile_icon_id, int) and profile_icon_id >= 0:
                    try:
                        latest_version = await self.get_latest_ddragon_version(session)
                        embed.set_thumbnail(
                            url=f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/img/profileicon/{profile_icon_id}.png"
                        )
                    except Exception as e:
                        logger.error(f"Error setting profile icon thumbnail: {e}")
                else:
                    logger.error(f"Invalid or missing profileIconId for {riotid} in region {region}. Summoner data: {summoner_data}")

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

                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")

                conditional_embed = await get_conditional_embed(interaction, 'LEAGUE_EMBED', discord.Color.orange())
                embeds = [embed]
                if conditional_embed:
                    embeds.append(conditional_embed)
                
                view = LeagueProfileView(self, puuid, region, riotid, str(interaction.user.id))
                message = await interaction.followup.send(embeds=embeds, view=view)
                view.message = message

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

    async def fetch_league_data(self, session: aiohttp.ClientSession, puuid: str, region: str,
                                headers: dict) -> dict:
        try:
            league_url = f"https://{region.lower()}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
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
            puuid = player['puuid']
            team_id = player['teamId']
            current_time = time.time()
            cached_account_data = account_data_cache.get(puuid)

            if cached_account_data and current_time - cached_account_data['timestamp'] < CACHE_EXPIRY_SECONDS:
                account_data = cached_account_data['data']
            else:
                account_url = f"https://{region.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
                summoner_data = await self.fetch_data(session, account_url, headers)

                if summoner_data and 'puuid' in summoner_data:
                    riot_id_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-puuid/{summoner_data['puuid']}"
                    account_data = await self.fetch_data(session, riot_id_url, headers)
                    if account_data:
                        account_data_cache[puuid] = {'data': account_data, 'timestamp': current_time}
                else:
                    account_data = None

            if account_data:
                game_name = account_data.get('gameName', 'Unknown')
                tag_line = account_data.get('tagLine', '')
                riotId = f"{game_name}#{tag_line}" if tag_line else game_name
            else:
                # Try riotId first, then summonerName, finally default to 'Unknown'
                riotId = player.get('riotId') or player.get('summonerName', 'Unknown')

            rank = await self.get_player_rank(session, puuid, region, headers)
            champion_id = player['championId']
            champion_name = await self.fetch_champion_name(session, champion_id)

            return {'riotId': riotId, 'champion_name': champion_name, 'rank': rank}, team_id
        except Exception as e:
            logger.error(f"Error fetching participant data: {e}")
            return {'riotId': 'Unknown', 'champion_name': 'Unknown', 'rank': 'Unranked'}, player.get('teamId', 0)

    async def get_player_rank(self, session: aiohttp.ClientSession, puuid: str, region: str,
                              headers: dict) -> str:
        try:
            league_data = await self.fetch_league_data(session, puuid, region, headers)
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

    async def get_latest_ddragon_version(self, session: aiohttp.ClientSession) -> str:
        """Get the latest Data Dragon version."""
        try:
            versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
            versions_data = await self.fetch_data(session, versions_url)
            return versions_data[0] if versions_data else '13.1.1'
        except Exception as e:
            logger.error(f"Error fetching Data Dragon version: {e}")
            return '13.1.1'

    async def fetch_champion_name(self, session: aiohttp.ClientSession, champion_id: int) -> str:
        try:
            latest_version = await self.get_latest_ddragon_version(session)

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
            # First, handle special cases like "Wukong" -> "MonkeyKing"
            if champion_name in SPECIAL_EMOJI_NAMES:
                base_name = SPECIAL_EMOJI_NAMES[champion_name]
            else:
                # For all others, remove apostrophes, spaces, and other non-alphanumeric characters
                base_name = re.sub(r'[^a-zA-Z0-9]', '', champion_name)
            
            # Construct the emoji name in the format 'championname_0'
            emoji_key = f"{base_name}_0".lower()
            
            # Look up the emoji in the cache
            emoji = self.emojis.get(emoji_key)

            if not emoji:
                # Fallback for champions who might not have the '_0' suffix for some reason
                fallback_key = base_name.lower()
                emoji = self.emojis.get(fallback_key, "") # Default to empty string if not found
                if not emoji:
                    logger.debug(f"Emoji not found for champion '{champion_name}'. Looked for keys: '{emoji_key}', '{fallback_key}'")
            return emoji
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

    async def fetch_match_ids(self, session: aiohttp.ClientSession, puuid: str, region: str, headers: dict, count: int = 5) -> List[str]:
        """Fetch recent match IDs for a player."""
        try:
            routing = REGION_TO_ROUTING.get(region.upper(), "europe")
            url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
            data = await self.fetch_data(session, url, headers)
            return data if data else []
        except Exception as e:
            logger.error(f"Failed to fetch match IDs: {e}")
            return []

    async def fetch_match_details(self, session: aiohttp.ClientSession, match_id: str, region: str, headers: dict) -> Optional[dict]:
        """Fetch details for a specific match."""
        try:
            routing = REGION_TO_ROUTING.get(region.upper(), "europe")
            url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            return await self.fetch_data(session, url, headers)
        except Exception as e:
            logger.error(f"Failed to fetch match details for {match_id}: {e}")
            return None

    def get_champion_display_name(self, api_name: str) -> str:
        """Convert API champion name to proper display name using SPECIAL_EMOJI_NAMES."""
        # Reverse lookup: find display name from internal name
        for display_name, internal_name in SPECIAL_EMOJI_NAMES.items():
            if internal_name.lower() == api_name.lower() or internal_name.lower() == api_name.replace("'", "").replace(" ", "").lower():
                return display_name
        # Add spaces before capitals for names like "MissFortune" -> "Miss Fortune"
        spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', api_name)
        return spaced

    async def create_match_history_embed(self, session: aiohttp.ClientSession, puuid: str, region: str, headers: dict, riotid: str) -> discord.Embed:
        """Create an embed displaying recent match history."""
        embed = discord.Embed(
            title=f"📜 Match History - {riotid}",
            color=0x1a78ae,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        match_ids = await self.fetch_match_ids(session, puuid, region, headers, count=9)
        if not match_ids:
            embed.description = "No recent matches found."
            embed.set_footer(text="AstroStats | astrostats.info")
            return embed
        matches_data = await asyncio.gather(*[self.fetch_match_details(session, mid, region, headers) for mid in match_ids])
        for match_data in matches_data:
            if not match_data:
                continue
            info = match_data.get('info', {})
            participants = info.get('participants', [])
            player = next((p for p in participants if p.get('puuid') == puuid), None)
            if not player:
                continue
            # Result with emoji
            win = player.get('win', False)
            result_emoji = "✅" if win else "❌"
            result_text = "Victory" if win else "Defeat"
            # Champion with proper display name
            champion_api = player.get('championName', 'Unknown')
            champion_display = self.get_champion_display_name(champion_api)
            champ_emoji = await self.get_emoji_for_champion(champion_display)
            # Key stats - KDA
            kills = player.get('kills', 0)
            deaths = player.get('deaths', 0)
            assists = player.get('assists', 0)
            kda_ratio = (kills + assists) / max(deaths, 1)
            # Game details - duration
            duration_secs = info.get('gameDuration', 0)
            duration_mins = duration_secs // 60
            duration_secs_rem = duration_secs % 60
            # Build field: Result • Champion | KDA | Duration
            field_name = f"{result_emoji} {result_text} • {champ_emoji}{champion_display}"
            field_value = f"**{kills}/{deaths}/{assists}** ({kda_ratio:.1f} KDA)\n⏱️ {duration_mins}:{duration_secs_rem:02d}"
            embed.add_field(name=field_name, value=field_value, inline=True)
        if not embed.fields:
            embed.description = "No match data available."
        embed.set_footer(text="AstroStats | astrostats.info")
        return embed

    async def create_champion_mastery_embed(self, session: aiohttp.ClientSession, puuid: str, region: str, headers: dict, riotid: str) -> discord.Embed:
        """Create an embed displaying champion mastery data."""
        embed = discord.Embed(
            title=f"🏆 Champion Mastery - {riotid}",
            color=0x1a78ae,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        mastery_url = f"https://{region.lower()}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
        mastery_data = await self.fetch_data(session, mastery_url, headers)
        if not mastery_data:
            embed.description = "No champion mastery data found."
            embed.set_footer(text="AstroStats | astrostats.info")
            return embed
        top_masteries = mastery_data[:10]
        description_lines = []
        for mastery in top_masteries:
            champion_id = mastery.get("championId")
            champion_name = await self.fetch_champion_name(session, champion_id)
            emoji = await self.get_emoji_for_champion(champion_name)
            mastery_level = mastery.get("championLevel", "N/A")
            mastery_points = mastery.get("championPoints", "N/A")
            if mastery_points != "N/A":
                mastery_points = f"{mastery_points:,}"
            description_lines.append(f"{emoji} **{champion_name}** • Mastery {mastery_level} • {mastery_points} pts")
        embed.description = "\n".join(description_lines)
        embed.set_footer(text="AstroStats | astrostats.info")
        return embed


class LeagueProfileView(View):
    """View with Match History and Champion Mastery buttons for League profile."""
    def __init__(self, cog: 'LeagueCog', puuid: str, region: str, riotid: str, user_id: str):
        super().__init__(timeout=840)
        self.cog = cog
        self.puuid = puuid
        self.region = region
        self.riotid = riotid
        self.user_id = user_id
        self.message: Optional[discord.Message] = None
        self._add_premium_buttons()

    async def on_timeout(self) -> None:
        """Disable all buttons when the view times out."""
        try:
            for child in self.children:
                if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                    child.disabled = True
            
            if self.message:
                await self.message.edit(view=self)
        except discord.HTTPException as e:
            if e.code == 50027:
                # 50027: Invalid Webhook Token (token expired after 15 mins)
                # No need to log this as an error since it's expected behavior for old messages
                logger.debug(f"Interaction token expired while handling timeout for LeagueProfileView")
            else:
                logger.error(f"HTTP error handling timeout for LeagueProfileView: {e}")
        except Exception as e:
            logger.error(f"Unexpected error handling timeout for LeagueProfileView: {e}")

    def _add_premium_buttons(self):
        """Add premium promotion buttons."""
        try:
            from services.premium import get_user_entitlements
            entitlements = get_user_entitlements(self.user_id)
            tier = (entitlements or {}).get("tier", "free")
            if tier == "free":
                btn = Button(label="Get Premium", style=discord.ButtonStyle.link, url="https://astrostats.info/pricing", emoji="💎")
            else:
                btn = Button(label="Manage Account", style=discord.ButtonStyle.link, url="https://astrostats.info/account", emoji="⚙️")
            self.add_item(btn)
            nom_btn = Button(label="Nominate AstroStats", style=discord.ButtonStyle.link, url="https://top.gg/bot/1088929834748616785", emoji="🏅")
            self.add_item(nom_btn)
        except Exception:
            pass

    @discord.ui.button(label="Match History", style=discord.ButtonStyle.primary, emoji="📜")
    async def match_history_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        try:
            riot_api_key = LOL_API
            if not riot_api_key:
                await interaction.followup.send("API key not configured.", ephemeral=True)
                return
            headers = {'X-Riot-Token': riot_api_key}
            async with aiohttp.ClientSession() as session:
                embed = await self.cog.create_match_history_embed(session, self.puuid, self.region, headers, self.riotid)
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error fetching match history: {e}")
            await interaction.followup.send("Failed to fetch match history. Please try again later.", ephemeral=True)

    @discord.ui.button(label="Champion Mastery", style=discord.ButtonStyle.secondary, emoji="🏆")
    async def champion_mastery_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        try:
            riot_api_key = LOL_API
            if not riot_api_key:
                await interaction.followup.send("API key not configured.", ephemeral=True)
                return
            headers = {'X-Riot-Token': riot_api_key}
            async with aiohttp.ClientSession() as session:
                embed = await self.cog.create_champion_mastery_embed(session, self.puuid, self.region, headers, self.riotid)
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error fetching champion mastery: {e}")
            await interaction.followup.send("Failed to fetch champion mastery. Please try again later.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeagueCog(bot))

import os
import asyncio
import datetime
import logging
from typing import Literal, Optional, List
from urllib.parse import urlencode

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button

from config.settings import TFT_API
from config.constants import LEAGUE_REGIONS, TFT_QUEUE_TYPE_NAMES, REGION_TO_ROUTING
from core.utils import get_conditional_embed
from core.errors import send_error_embed
from ui.embeds import get_premium_promotion_view
from services.compare_image import compare_image_generator, compare_values

logger = logging.getLogger(__name__)


class TFTCog(commands.GroupCog, group_name="tft"):
    """A cog grouping TFT commands under `/tft`."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    async def fetch_data(self, session: aiohttp.ClientSession, url: str, headers: dict = None) -> Optional[dict]:
        """Fetch data from an API endpoint."""
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
                    logger.error(f"Error fetching data from {url}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception during fetch_data: {e}")
            return None

    async def get_latest_ddragon_version(self, session: aiohttp.ClientSession) -> str:
        """Get the latest Data Dragon version."""
        try:
            versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
            versions_data = await self.fetch_data(session, versions_url)
            return versions_data[0] if versions_data else '13.1.1'
        except Exception as e:
            logger.error(f"Error fetching Data Dragon version: {e}")
            return '13.1.1'

    async def fetch_match_ids(self, session: aiohttp.ClientSession, puuid: str, region: str, headers: dict, count: int = 5) -> List[str]:
        """Fetch recent TFT match IDs for a player."""
        try:
            routing = REGION_TO_ROUTING.get(region.upper(), "europe")
            url = f"https://{routing}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
            data = await self.fetch_data(session, url, headers)
            return data if data else []
        except Exception as e:
            logger.error(f"Failed to fetch TFT match IDs: {e}")
            return []

    async def fetch_match_details(self, session: aiohttp.ClientSession, match_id: str, region: str, headers: dict) -> Optional[dict]:
        """Fetch details for a specific TFT match."""
        try:
            routing = REGION_TO_ROUTING.get(region.upper(), "europe")
            url = f"https://{routing}.api.riotgames.com/tft/match/v1/matches/{match_id}"
            return await self.fetch_data(session, url, headers)
        except Exception as e:
            logger.error(f"Failed to fetch TFT match details for {match_id}: {e}")
            return None

    async def create_match_history_embed(self, session: aiohttp.ClientSession, puuid: str, region: str, headers: dict, riotid: str) -> discord.Embed:
        """Create an embed displaying recent TFT match history."""
        embed = discord.Embed(
            title=f"📜 TFT Match History - {riotid}",
            color=0x1a78ae,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        match_ids = await self.fetch_match_ids(session, puuid, region, headers, count=9)
        if not match_ids:
            embed.description = "No recent matches found."
            embed.set_footer(text="AstroStats | astrostats.info")
            return embed
        matches_data = await asyncio.gather(*[self.fetch_match_details(session, mid, region, headers) for mid in match_ids])
        placement_emojis = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣"}
        for match_data in matches_data:
            if not match_data:
                continue
            info = match_data.get('info', {})
            participants = info.get('participants', [])
            player = next((p for p in participants if p.get('puuid') == puuid), None)
            if not player:
                continue
            placement = player.get('placement', 0)
            placement_emoji = placement_emojis.get(placement, f"#{placement}")
            level = player.get('level', 0)
            traits = player.get('traits', [])
            active_traits = sorted([t for t in traits if t.get('tier_current', 0) > 0], key=lambda x: x.get('tier_current', 0), reverse=True)[:2]
            trait_names = ", ".join([t.get('name', '').replace('Set13_', '').replace('Set12_', '').replace('Set11_', '') for t in active_traits]) or "-"
            duration_secs = info.get('game_length', 0)
            duration_mins = int(duration_secs // 60)
            duration_secs_rem = int(duration_secs % 60)
            field_name = f"{placement_emoji} #{placement} • Lvl {level}"
            field_value = f"{trait_names}\n{duration_mins}:{duration_secs_rem:02d}"
            embed.add_field(name=field_name, value=field_value, inline=True)
        if not embed.fields:
            embed.description = "No match data available."
        embed.set_footer(text="AstroStats | astrostats.info")
        return embed

    async def _fetch_player_profile(self, session, game_name, tag_line, region, headers):
        """Fetch all TFT profile data for a player. Returns dict or None."""
        regional_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        account_data = await self.fetch_data(session, regional_url, headers)
        if not account_data:
            return None

        puuid = account_data.get('puuid')
        if not puuid:
            return None

        summoner_url = f"https://{region.lower()}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
        summoner_data = await self.fetch_data(session, summoner_url, headers)
        if not summoner_data:
            return None

        league_url = f"https://{region.lower()}.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
        league_data = await self.fetch_data(session, league_url, headers)

        ranked_info = {"display": "Unranked", "tier": "Unranked", "rank": "", "lp": 0, "wins": 0, "losses": 0, "winrate": 0}
        if league_data:
            for league_info in league_data:
                queue_type = TFT_QUEUE_TYPE_NAMES.get(league_info.get('queueType'), None)
                if queue_type:
                    tier = league_info.get('tier', 'Unranked')
                    rank = league_info.get('rank', '')
                    lp = league_info.get('leaguePoints', 0)
                    wins = league_info.get('wins', 0)
                    losses = league_info.get('losses', 0)
                    total_games = wins + losses
                    winrate = int((wins / total_games) * 100) if total_games > 0 else 0
                    ranked_info = {
                        "display": f"{tier} {rank} {lp} LP\nW: {wins} / L: {losses} ({winrate}%)",
                        "tier": tier, "rank": rank, "lp": lp,
                        "wins": wins, "losses": losses, "winrate": winrate
                    }
                    break

        return {
            "puuid": puuid,
            "summoner_data": summoner_data,
            "league_data": league_data,
            "ranked_info": ranked_info,
            "game_name": game_name,
            "tag_line": tag_line,
            "riotid": f"{game_name}#{tag_line}",
            "level": summoner_data.get('summonerLevel', 0),
            "profile_icon_id": summoner_data.get('profileIconId'),
        }

    @app_commands.command(name="stats", description="Check your TFT Player Stats!")
    async def stats(self, interaction: discord.Interaction, region: Literal[
        "EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2", "JP1", "KR", "OC1", "SG2", "TW2", "VN2"], riotid: str):
        try:
            await interaction.response.defer()
            if "#" not in riotid:
                await send_error_embed(
                    interaction,
                    "Invalid Format",
                    "Please enter both your game name and tag line in the format `gameName#tagLine`."
                )
                return

            game_name, tag_line = riotid.split("#")
            riot_api_key = TFT_API
            if not riot_api_key:
                logger.error("TFT API key is missing")
                await send_error_embed(
                    interaction,
                    "Configuration Error",
                    "TFT API key is not configured. Please contact the bot owner."
                )
                return

            headers = {'X-Riot-Token': riot_api_key}
            async with aiohttp.ClientSession() as session:
                regional_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
                account_data = await self.fetch_data(session, regional_url, headers)
                if not account_data:
                    await send_error_embed(
                        interaction,
                        "Summoner Not Found",
                        "Summoner not found. Please check your Riot ID and try again."
                    )
                    return

                puuid = account_data.get('puuid')
                if not puuid:
                    logger.error("PUUID not found in the API response.")
                    await send_error_embed(
                        interaction,
                        "Data Error",
                        "Failed to retrieve summoner data. Please ensure your Riot ID is correct and try again."
                    )
                    return

                summoner_url = f"https://{region.lower()}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
                summoner_data = await self.fetch_data(session, summoner_url, headers)
                if not summoner_data:
                    await send_error_embed(
                        interaction,
                        "Region Error",
                        f"Failed to retrieve summoner data for the region {region}."
                    )
                    return

                league_url = f"https://{region.lower()}.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
                league_data = await self.fetch_data(session, league_url, headers)

                query_params = urlencode({"gameName": game_name, "tagLine": tag_line, "region": region})
                profile_url = f"https://www.clutchgg.lol/tft/profile?{query_params}"

                embed = discord.Embed(
                    title=f"{game_name}#{tag_line} - Level {summoner_data['summonerLevel']}",
                    color=0x1a78ae,
                    url=profile_url
                )
                profile_icon_id = summoner_data.get('profileIconId')
                if profile_icon_id is not None:
                    latest_version = await self.get_latest_ddragon_version(session)
                    embed.set_thumbnail(
                        url=f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/img/profileicon/{profile_icon_id}.png"
                    )

                if league_data:
                    for league_info in league_data:
                        queue_type = TFT_QUEUE_TYPE_NAMES.get(league_info['queueType'], "Other")
                        tier = league_info['tier']
                        rank = league_info['rank']
                        lp = league_info['leaguePoints']
                        wins = league_info['wins']
                        losses = league_info['losses']
                        total_games = wins + losses
                        winrate = int((wins / total_games) * 100) if total_games > 0 else 0
                        league_info_str = f"{tier} {rank} {lp} LP\nWins: {wins}\nLosses: {losses}\nWinrate: {winrate}%"
                        embed.add_field(name=queue_type, value=league_info_str, inline=False)
                else:
                    embed.add_field(name="Rank", value="Unranked", inline=False)

                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")

                conditional_embed = await get_conditional_embed(interaction, 'TFT_EMBED', discord.Color.orange())
                embeds = [embed]
                if conditional_embed:
                    embeds.append(conditional_embed)

                view = TFTMatchHistoryView(self, puuid, region, riotid, str(interaction.user.id))
                await interaction.followup.send(embeds=embeds, view=view)

        except aiohttp.ClientError as e:
            logger.error(f"Request Error: {e}")
            await send_error_embed(
                interaction,
                "Connection Error",
                "Sorry, I couldn't retrieve Teamfight Tactics stats at the moment. Please try again later."
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Data Error: {e}")
            await send_error_embed(
                interaction,
                "Data Error",
                "Failed to retrieve summoner data. Please ensure your Riot ID is correct and try again."
            )
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            await send_error_embed(
                interaction,
                "Unexpected Error",
                "Oops! An unexpected error occurred while processing your request. Please try again later."
            )


    @app_commands.command(name="compare", description="Compare two TFT players side-by-side")
    async def compare(
            self,
            interaction: discord.Interaction,
            region: Literal["EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2", "JP1", "KR", "OC1", "SG2", "TW2", "VN2"],
            riotid1: str,
            riotid2: str
    ):
        try:
            await interaction.response.defer()

            for rid, label in [(riotid1, "first"), (riotid2, "second")]:
                if "#" not in rid:
                    await send_error_embed(
                        interaction,
                        "Invalid Format",
                        f"The {label} Riot ID must be in the format `gameName#tagLine`."
                    )
                    return

            game_name1, tag_line1 = riotid1.split("#", 1)
            game_name2, tag_line2 = riotid2.split("#", 1)

            riot_api_key = TFT_API
            if not riot_api_key:
                await send_error_embed(interaction, "Configuration Error", "TFT API key is not configured.")
                return
            headers = {'X-Riot-Token': riot_api_key}

            async with aiohttp.ClientSession() as session:
                p1, p2 = await asyncio.gather(
                    self._fetch_player_profile(session, game_name1, tag_line1, region, headers),
                    self._fetch_player_profile(session, game_name2, tag_line2, region, headers)
                )

                errors = []
                if not p1:
                    errors.append(f"Could not find **{riotid1}** in **{region}**.")
                if not p2:
                    errors.append(f"Could not find **{riotid2}** in **{region}**.")
                if errors:
                    await send_error_embed(interaction, "Player Not Found", "\n".join(errors), notify_logged=False)
                    return

                rows = self._build_compare_rows(p1, p2)
                img_buf = compare_image_generator.create_image(
                    title="TFT Comparison",
                    player1_name=p1['riotid'],
                    player2_name=p2['riotid'],
                    rows=rows,
                    accent_color=(26, 120, 174),
                    subtitle=f"Region: {region}",
                )

                if img_buf:
                    await interaction.followup.send(
                        file=discord.File(img_buf, "tft_compare.png")
                    )
                else:
                    await send_error_embed(interaction, "Image Error", "Failed to generate comparison image.")

        except aiohttp.ClientError as e:
            logger.error(f"Request Error in TFT compare: {e}")
            await send_error_embed(interaction, "API Error", "Could not retrieve TFT stats. Please try again later.")
        except Exception as e:
            logger.error(f"Unexpected Error in TFT compare: {e}")
            await send_error_embed(interaction, "Unexpected Error", "An unexpected error occurred. Please try again later.")

    def _build_compare_rows(self, p1, p2):
        """Build comparison rows for the image generator."""
        rows = []

        # Level
        lvl1, lvl2 = p1['level'], p2['level']
        s1, s2 = compare_values(lvl1, lvl2, str(lvl1), str(lvl2))
        rows.append(("Level", s1, s2))

        ri1 = p1['ranked_info']
        ri2 = p2['ranked_info']

        # Rank tier
        t1 = f"{ri1['tier']} {ri1['rank']}" if ri1['tier'] != "Unranked" else "Unranked"
        t2 = f"{ri2['tier']} {ri2['rank']}" if ri2['tier'] != "Unranked" else "Unranked"
        rows.append(("Ranked TFT", t1, t2))

        # LP
        lp1, lp2 = ri1['lp'], ri2['lp']
        ls1, ls2 = compare_values(lp1, lp2, f"{lp1} LP", f"{lp2} LP")
        rows.append(("League Points", ls1, ls2))

        # Wins
        w1, w2 = ri1['wins'], ri2['wins']
        ws1, ws2 = compare_values(w1, w2, str(w1), str(w2))
        rows.append(("Wins", ws1, ws2))

        # Losses
        l1, l2 = ri1['losses'], ri2['losses']
        lls1, lls2 = compare_values(l1, l2, str(l1), str(l2), higher_is_better=False)
        rows.append(("Losses", lls1, lls2))

        # Winrate
        wr1, wr2 = ri1['winrate'], ri2['winrate']
        wrs1, wrs2 = compare_values(wr1, wr2, f"{wr1}%", f"{wr2}%")
        rows.append(("Win Rate", wrs1, wrs2))

        return rows


class TFTMatchHistoryView(View):
    """View with Match History button for TFT profile."""
    def __init__(self, cog: 'TFTCog', puuid: str, region: str, riotid: str, user_id: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.puuid = puuid
        self.region = region
        self.riotid = riotid
        self.user_id = user_id
        self._add_premium_buttons()

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
        except Exception:
            pass

    @discord.ui.button(label="Match History", style=discord.ButtonStyle.primary, emoji="📜")
    async def match_history_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        try:
            riot_api_key = TFT_API
            if not riot_api_key:
                await interaction.followup.send("API key not configured.", ephemeral=True)
                return
            headers = {'X-Riot-Token': riot_api_key}
            async with aiohttp.ClientSession() as session:
                embed = await self.cog.create_match_history_embed(session, self.puuid, self.region, headers, self.riotid)
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error fetching TFT match history: {e}")
            await interaction.followup.send("Failed to fetch match history. Please try again later.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TFTCog(bot))

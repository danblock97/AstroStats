import discord
import datetime
import aiohttp
import os
import logging
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
    "CHERRY": "Arena"
}

# Dictionary to store the last fetch time for each user
last_fetch_times = defaultdict(lambda: datetime.datetime.min)

# Global dictionary to store emojis
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
    "Lee Sin": "LeeSin"
}

# Helper function to fetch data from an API
async def fetch_data(url: str, headers=None) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                logging.error(f"Error fetching data from {url}: {response.status}")
                return None
            return await response.json()

# Helper function to fetch a player's game name and tagline using PUUID
async def fetch_game_name_tagline(puuid: str, headers: dict) -> dict:
    regional_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    return await fetch_data(regional_url, headers)

# Helper function to fetch summoner data by PUUID
async def fetch_summoner_data(puuid: str, region: str, headers: dict) -> dict:
    summoner_url = f"https://{region.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return await fetch_data(summoner_url, headers)

# Helper function to fetch league data by summoner ID
async def fetch_league_data(summoner_id: str, region: str, headers: dict) -> dict:
    league_url = f"https://{region.lower()}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    return await fetch_data(league_url, headers)

# Helper function to fetch champion name by champion ID
async def fetch_champion_name(champion_id: int) -> str:
    url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champions/{champion_id}.json"
    data = await fetch_data(url)
    return data.get('name', 'Unknown') if data else "Unknown"

# Helper function to get player's rank
async def get_player_rank(puuid: str, region: str, headers: dict) -> str:
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

# Helper function to get emoji for a champion
async def get_emoji_for_champion(champion_name: str) -> str:
    global emojis
    if not emojis:
        emoji_data = await fetch_application_emojis()
        if emoji_data:
            for emoji in emoji_data:
                # Validate if the emoji is in the correct format
                if isinstance(emoji, dict) and 'name' in emoji and 'id' in emoji:
                    normalized_name = emoji['name'].split('_')[0].lower()
                    emojis[normalized_name] = f"<:{emoji['name']}:{emoji['id']}>"
                else:
                    logging.error(f"Invalid emoji format detected: {emoji}")

    # Check if the champion name has a special emoji name
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

            # Ensure the returned data is a list of emoji objects
            if isinstance(data, dict) and 'items' in data:
                data = data['items']
            elif not isinstance(data, list):
                logging.error("Unexpected emoji data format")
                return None
            
            # Validate each emoji entry
            valid_emojis = []
            for emoji in data:
                if isinstance(emoji, dict) and 'name' in emoji and 'id' in emoji:
                    valid_emojis.append(emoji)
                else:
                    logging.error(f"Unexpected emoji format: {emoji}")
            
            return valid_emojis if valid_emojis else None


# Helper function to send error embed
async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=f"{description}\n\nFor more assistance, visit [AstroStats Support](https://astrostats.vercel.app)",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.UTC)
    )
    await interaction.response.send_message(embed=embed)

# Main League of Legends command
async def league(interaction: discord.Interaction, riotid: str):
    try:
        await interaction.response.defer()

        # Validate riotid
        if "#" not in riotid:
            await send_error_embed(interaction, "Invalid Riot ID", "Please enter both your game name and tag line in the format gameName#tagLine.")
            return

        game_name, tag_line = riotid.split("#")
        riot_api_key = os.getenv('LOL_API')
        headers = {'X-Riot-Token': riot_api_key}

        # Fetch account data to get puuid
        regional_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        account_data = await fetch_data(regional_url, headers)
        puuid = account_data.get('puuid')

        if not puuid:
            await send_error_embed(interaction, "Account Not Found", "Failed to retrieve PUUID. Please ensure your Riot ID is correct.")
            return

        summoner_data, league_data, selected_region = None, None, None

        for region in REGIONS:
            summoner_data = await fetch_summoner_data(puuid, region, headers)
            if summoner_data:
                league_data = await fetch_league_data(summoner_data['id'], region, headers)
                if league_data:
                    selected_region = region
                    break

        if not league_data:
            await send_error_embed(interaction, "No Data Found", "Failed to retrieve league data. Player might not be active in the checked regions.")
            return

        # Build the embed message
        embed = discord.Embed(title=f"{game_name}#{tag_line} - Level {summoner_data['summonerLevel']}", color=0x1a78ae)
        embed.set_thumbnail(url=f"https://raw.communitydragon.org/latest/game/assets/ux/summonericons/profileicon{summoner_data['profileIconId']}.png")

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

        embed.timestamp = datetime.datetime.now(datetime.UTC)
        embed.set_footer(text="Built By Goldiez ❤️ Visit clutchgg.vercel.app for more!")

        # Add the view for live game if applicable
        view = create_live_game_view(interaction.client, embed, puuid, selected_region, headers, game_name, tag_line)
        await interaction.followup.send(embed=embed, view=view)

    except aiohttp.ClientError as e:
        logging.error(f"Request Error: {e}")
        await send_error_embed(interaction, "API Error", "Sorry, I couldn't retrieve League of Legends stats at the moment. Please try again later.")
    except (KeyError, ValueError) as e:
        logging.error(f"Data Error: {e}")
        await send_error_embed(interaction, "Data Error", "Failed to retrieve summoner data. Please ensure your Riot ID is correct.")
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        await send_error_embed(interaction, "Unexpected Error", "Oops! An unexpected error occurred while processing your request. Please try again later.")

# Helper function to create live game view
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

# Function to update live game view
async def update_live_game_view(interaction: discord.Interaction, embed, puuid, region, headers, live_game_button, game_name, tag_line, view):
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
        summoner_name = f"{account_data['gameName']}#{account_data['tagLine']}" if account_data else "Unknown"

        rank = await get_player_rank(player_puuid, region, headers)
        champion_id = player['championId']
        champion_name = await fetch_champion_name(champion_id)
        emoji = await get_emoji_for_champion(champion_name)

        player_data = {
            'summoner_name': summoner_name,
            'champion_name': f"{emoji} {champion_name}",
            'rank': rank
        }

        if player['teamId'] == 100:
            blue_team.append(player_data)
        else:
            red_team.append(player_data)

    embed.clear_fields()
    embed.title = "Live Game"

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

    live_game_button.label = 'Live Game'
    live_game_button.disabled = False
    await interaction.edit_original_response(view=view)

    last_fetch_times[puuid] = datetime.datetime.utcnow()

# Function to set up the League command
async def setup(client):
    client.tree.add_command(
        discord.app_commands.Command(
            name="league",
            description="Check your League of Legends Player Stats",
            callback=league
        )
    )

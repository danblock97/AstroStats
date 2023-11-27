import datetime
import discord
import os
from discord.ext import commands
import requests
from typing import Literal
from dotenv import load_dotenv
from riotwatcher import LolWatcher
from bs4 import BeautifulSoup
import requests

signs = {
    "aries": 1,
    "taurus": 2,
    "gemini": 3,
    "cancer": 4,
    "leo": 5,
    "virgo": 6,
    "libra": 7,
    "scorpio": 8,
    "sagittarius": 9,
    "capricorn": 10,
    "aquarius": 11,
    "pisces": 12,
}

client = commands.Bot(command_prefix="/", help_command=None,
                      intents=discord.Intents.all())

load_dotenv()

key = os.getenv('RIOT_API')
lolWatcher = LolWatcher(key)


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

    # Get the list of servers the bot is a member of
    servers = client.guilds
    for server in servers:
        print(f'Bot is a member of: {server.name} ({server.id})')
    try:
        synced = await client.tree.sync()
        print(f"Commands Synced")
    except Exception as e:
        print(e)
    guild_count = len(client.guilds)
    presence = discord.Activity(type=discord.ActivityType.playing, name=f"on {guild_count} servers")
    await client.change_presence(activity=presence)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # Log the guild ID and the command that was not found
        print(f'CommandNotFound in Guild {ctx.guild.id}: {ctx.message.content}')
    else:
        pass
    
# Get the blacklisted server IDs from the .env file
blacklisted_server_ids = [int(server_id) for server_id in os.getenv('BLACKLISTED_SERVER_IDS', '').split(',')]

@client.event
async def on_invite_create(invite):
    # Check if the server ID is in the whitelist
    if invite.guild.id not in blacklisted_server_ids:
        await invite.delete()
        print(f"Removed invite for server {invite.guild.id} from {invite.inviter.id} due to blacklist restrictions.")
    
@client.tree.command(name="help", description="Lists all available commands")
async def help(interaction: discord.Interaction):
    guild_count = len(client.guilds)
    embed = discord.Embed(title=f"NexusBot - Trusted by {guild_count} servers", color=0xdd4f7a)
    embed.add_field(name="Apex Legends Lifetime Stats",
                    value="`/apex <username> <xbl/psn/origin>`")
    embed.add_field(name="LoL Player Stats",
                    value="`/profile <summoner name>`")
    embed.add_field(name="Fortnite Player Stats",
                    value="`/fortnite <name>`")
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="review", description="Leave a review on Top.gg")
async def review(interaction: discord.Interaction):
    review_message = "If you're enjoying AstroStats, please consider leaving a review on Top.gg! " \
                     "https://top.gg/bot/1088929834748616785#reviews"
    await interaction.response.send_message(review_message)

@client.tree.command(name="apex", description="Check your Apex Lifetime Stats")
async def apex(interaction: discord.Interaction, name: str = None, platform: str = None):
    if name is None:
        await interaction.response.send_message("`/apex <username>`")
        return
    if platform is None:
        await interaction.response.send_message("`/apex <xbl/psn/origin>`")
        return

    response = requests.get(f"https://public-api.tracker.gg/v2/apex/standard/profile/{platform}/{name}",
                            headers={"TRN-Api-Key": os.getenv('TRN-Api-Key')})

    if response.status_code == 200:
        data = response.json()
        segments = data['data']['segments'][0]
        stats = segments['stats']

        embed = discord.Embed(title=f"Apex Legends - Lifetime Overview",
                              url=f"https://apex.tracker.gg/apex/profile/{platform}/{name}", color=0xdd4f7a)
        
        print(f'{client.user} has retrieved your Apex stats!')

        for key, value in stats.items():
            if isinstance(value, dict):
                embed.add_field(
                    name=value['displayName'], value=value['displayValue'], inline=True)
            embed.timestamp = datetime.datetime.utcnow()
            embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Failed to retrieve your Apex stats. The TRN API is Currently Unavailable")


@client.tree.command(name="league", description="Check your LoL Player Stats")
async def league(interaction: discord.Interaction, *, summoner: str):
    summoner = lolWatcher.summoner.by_name('euw1', summoner)
    stats = lolWatcher.league.by_summoner('euw1', summoner['id'])
    num = 0
    if (stats[0]['queueType'] == 'RANKED_SOLO_5x5'):
        num = 0
    else:
        num = 1
    tier = stats[num]['tier']
    rank = stats[num]['rank']
    lp = stats[num]['leaguePoints']
    wins = int(stats[num]['wins'])
    losses = int(stats[num]['losses'])
    wr = int((wins/(wins+losses)) * 100)
    hotStreak = int(stats[num]['hotStreak'])
    level = int(summoner['summonerLevel'])
    icon = int(summoner['profileIconId'])
    embed = discord.Embed(
        title=f"League of Legends - Player Stats", color=0xdd4f7a)
    print(f'{client.user} has retrieved your LoL stats!')
    embed.set_thumbnail(
        url=f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{icon}.jpg")
    embed.add_field(name="Ranked Solo/Duo",
                    value=f'{str(tier)} {str(rank)} {str(lp)} LP \n Winrate: {str(wr)}% \n Winstreak: {str(hotStreak)}')
    embed.add_field(name="Level", value=f'{str(level)}')
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await interaction.response.send_message(embed=embed)


@client.event
async def p_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.MissingRequiredArguments):
        await interaction.response.send_message('Please specify a summoner name')


@client.tree.command(name="fortnite", description="Check your Fortnite Player Stats")
async def fortnite(interaction: discord.Interaction, *, name: str):
    response = requests.get(f"https://fortnite-api.com/v2/stats/br/v2?timeWindow=season&name={name}",
                            headers={"Authorization": os.getenv('FORTNITE_API_KEY')})

    try:
        data = response.json()

        if 'data' not in data:
            await interaction.response.send_message('Failed to retrieve Fortnite stats. The Fortnite API is Currently Unavailable')
            return

        stats = data['data']
        account = stats['account']
        battlePass = stats['battlePass']

        embed = discord.Embed(title=f"Fortnite - Player Stats", color=0xdd4f7a)
        print(f'{client.user} has retrieved Fortnite stats!')

        embed.add_field(name="Account", value=f"Name: {account['name']}\nLevel: {battlePass['level']}")
        embed.add_field(name="Season Stats",
                        value=f"Matches: {stats['stats']['all']['overall']['matches']}\nKills: {stats['stats']['all']['overall']['kills']}\nWins: {stats['stats']['all']['overall']['wins']}")
        embed.add_field(name="Match Placements",
                        value=f"Top 5: {stats['stats']['all']['overall']['top5']}\nTop 12: {stats['stats']['all']['overall']['top12']}")
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await interaction.response.send_message(embed=embed)

    except (KeyError, ValueError):
        await interaction.response.send_message("Failed to retrieve Fortnite stats. The Fortnite API is Currently Unavailable")

@client.event
async def p_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.MissingRequiredArguments):
        await interaction.response.send_message("Failed to retrieve LoL stats. The Riot API is Currently Unavailable")

@client.tree.command(name="horoscope", description="Check your horoscope for a specific star sign")
async def horoscope(interaction: discord.Interaction, sign: Literal['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']):
    given_sign = sign.lower()  # Convert to lowercase to match the URL format

    URL = "https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx?sign=" + str(signs[given_sign])

    r = requests.get(URL)
    soup = BeautifulSoup(r.text, 'html.parser')

    container = soup.find("p")

    horoscope_text = container.text.strip()

    embed = discord.Embed(title=f"Horoscope for {sign.capitalize()}", color=0xdd4f7a)
    embed.add_field(name="Today's Horoscope", value=horoscope_text, inline=False)
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await interaction.response.send_message(embed=embed)

client.run(os.getenv('TOKEN'))
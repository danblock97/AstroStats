import datetime
import discord
import os
from discord.ext import commands
import requests
from dotenv import load_dotenv
from riotwatcher import LolWatcher
from googletrans import Translator

translator = Translator()

client = commands.Bot(command_prefix="!", help_command=None,
                      intents=discord.Intents.all())

load_dotenv()

key = os.getenv('RIOT_API')
lolWatcher = LolWatcher(key)


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    try:
        synced = await client.tree.sync()
        print(f"Commands Synced")
    except Exception as e:
        print(e)
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="/help"))


@client.tree.command(name="help", description="Lists all available commands")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="NexusBot", color=0x1364a1)
    embed.add_field(name="CSGO Lifetime Stats", value="`/csgo <username>`")
    embed.add_field(name="Apex Legends Lifetime Stats",
                    value="`/apex <username> <xbl/psn/origin>`")
    embed.add_field(name="LoL Player Stats",
                    value="`/profile <summoner name>`")
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await interaction.response.send_message(embed=embed)


@client.tree.command(name="csgo", description="Check your CSGO Lifetime Stats")
async def csgo(interation: discord.Interaction, name: str = None):
    if name is None:
        await interation.response.send_message("`/apex <username>`")
        return

    response = requests.get(f"https://public-api.tracker.gg/v2/csgo/standard/profile/steam/{name}",
                            headers={"TRN-Api-Key": os.getenv('TRN-Api-Key')})

    if response.status_code == 200:
        data = response.json()
        segments = data['data']['segments'][0]
        stats = segments['stats']

        embed = discord.Embed(title=f"CSGO - Lifetime Overview",
                              url=f"https://tracker.gg/csgo/profile/steam/{name}", color=0x1364a1)
        for key, value in stats.items():
            print(f'{client.user} has retrieved your CSGO stats!')
            if isinstance(value, dict):
                embed.add_field(
                    name=value['displayName'], value=value['displayValue'], inline=True)
            embed.timestamp = datetime.datetime.utcnow()
            embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await interation.response.send_message(embed=embed)
    else:
        await interation.response.send_message("`/csgo <username>`")


@client.tree.command(name="apex", description="Check your Apex Lifetime Stats")
async def apex(interation: discord.Interaction, name: str = None, platform: str = None):
    if name is None:
        await interation.response.send_message("`/apex <username>`")
        return
    if platform is None:
        await interation.response.send_message("`/apex <xbl/psn/origin>`")
        return

    response = requests.get(f"https://public-api.tracker.gg/v2/apex/standard/profile/{platform}/{name}",
                            headers={"TRN-Api-Key": os.getenv('TRN-Api-Key')})

    if response.status_code == 200:
        data = response.json()
        segments = data['data']['segments'][0]
        stats = segments['stats']

        embed = discord.Embed(title=f"Apex Legends - Lifetime Overview",
                              url=f"https://apex.tracker.gg/apex/profile/{platform}/{name}", color=0x1364a1)
        for key, value in stats.items():
            print(f'{client.user} has retrieved your Apex stats!')
            if isinstance(value, dict):
                embed.add_field(
                    name=value['displayName'], value=value['displayValue'], inline=True)
            embed.timestamp = datetime.datetime.utcnow()
            embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await interation.response.send_message(embed=embed)
    else:
        await interation.response.send_message("`/apex <username>`")


@client.tree.command(name="league", description="Check your LoL Player Stats")
async def league(interactions: discord.Interaction, *, summoner: str):
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
        title=f"League of Legends - Player Stats", color=0x1364a1)
    print(f'{client.user} has retrieved your LoL stats!')
    embed.set_thumbnail(
        url=f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{icon}.jpg")
    embed.add_field(name="Ranked Solo/Duo",
                    value=f'{str(tier)} {str(rank)} {str(lp)} LP \n Winrate: {str(wr)}% \n Winstreak: {str(hotStreak)}')
    embed.add_field(name="Level", value=f'{str(level)}')
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await interactions.response.send_message(embed=embed)


@client.event
async def p_error(interactions: discord.Interaction, error):
    if isinstance(error, commands.MissingRequiredArguments):
        await interactions.response.send_message('Please specify a summoner name')


@client.tree.command(name="fortnite", description="Check your Fortnite Player Stats")
async def fortnite(interactions: discord.Interaction, *, name: str):
    response = requests.get(f"https://fortnite-api.com/v2/stats/br/v2?timeWindow=season&name={name}",
                            headers={"Authorization": os.getenv('FORTNITE_API_KEY')})

    data = response.json()

    if 'data' not in data:
        await interactions.response.send_message('Player not found')
        return

    stats = data['data']
    account = stats['account']
    battlePass = stats['battlePass']

    embed = discord.Embed(title=f"Fortnite - Player Stats", color=0x1364a1)
    print(f'{client.user} has retrieved Fortnite stats!')

    embed.add_field(
        name="Account", value=f'Name: {account["name"]} \n Level: {battlePass["level"]}')
    embed.add_field(name="Season Stats", 
                    value=f'Matches: {stats["stats"]["all"]["overall"]["matches"]} \n Kills: {stats["stats"]["all"]["overall"]["kills"]} \n Wins: {stats["stats"]["all"]["overall"]["wins"]}')
    embed.add_field(name="Match Placements", value=f'Top 5: {stats["stats"]["all"]["overall"]["top5"]} \n Top 12: {stats["stats"]["all"]["overall"]["top12"]}')
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await interactions.response.send_message(embed=embed)


@client.event
async def p_error(interactions: discord.Interaction, error):
    if isinstance(error, commands.MissingRequiredArguments):
        await interactions.response.send_message('Please specify a player name')

client.run(os.getenv('TOKEN'))

import datetime
import discord
import os
from discord.ext import commands
import requests
from dotenv import load_dotenv
from riotwatcher import LolWatcher

client = commands.Bot(command_prefix = "!", help_command=None, intents=discord.Intents.all())

load_dotenv()

key = os.getenv('RIOT_API')
watcher = LolWatcher(key)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    try:
        synced = await client.tree.sync()
        print(f"Commands Synced")
    except Exception as e:
        print(e)
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="NexusBot")) 

#/help
@client.tree.command(name="help", description="Lists all available commands")
async def help(interaction: discord.Interaction):
    embed=discord.Embed(title="NexusBot", color=0x1364a1)
    embed.add_field(name="CSGO Lifetime Stats", value="`/csgo`")
    embed.add_field(name="Apex Legends Lifetime Stats", value="`/apex`")
    embed.add_field(name="LoL Player Stats", value="`/lol`")
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await interaction.response.send_message(embed=embed)

#/csgo
@client.tree.command(name="csgo", description="Check your CSGO Lifetime Stats")
async def csgo(interaction: discord.Interaction, name: str = None):
    if name is None:
        await interaction.response.send_message("`!csgo <steamid_64>`")
        return

    # Make the API request
    response = requests.get(os.getenv('CSGO_API_URL').format(name), headers={"TRN-Api-Key": os.getenv('API_KEY')})

    if response.status_code == 200:
        data = response.json()
        segments = data['data']['segments'][0]
        stats = segments['stats']

        embed = discord.Embed(title=f"CS:GO - Lifetime Overview", url=os.getenv('CSGO_PROFILE_URL').format(name), color=0x1364a1)
        for key, value in stats.items():
            print(f'{client.user} has retrieved your CSGO stats!')
            if isinstance(stats, dict):
                    embed.add_field(name=value['displayName'], value=value['displayValue'], inline=True)
                    embed.timestamp = datetime.datetime.utcnow()
                    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await interaction.response.send_message(embed=embed) 
    else:
        await interaction.response.send_message("`!csgo <steamid_64>`")

#!apex
@client.tree.command(name="apex", description="Check your Apex Lifetime Stats")
async def apex(interation: discord.Interaction, name: str = None, platform: str = None ):
    if name is None:
        await interation.response.send_message("`!apex <steamid_64>`")
        if platform is None:
         await interation.response.send_message("`!apex <platform>`")
        return

    # Make the API request
    response = requests.get(os.getenv('APEX_API_URL').format(platform, name), headers={"TRN-Api-Key": os.getenv('API_KEY')}) 

    if response.status_code == 200:
        data = response.json()
        segments = data['data']['segments'][0]
        stats = segments['stats']

        embed = discord.Embed(title=f"Apex Legends - Lifetime Overview", url=os.getenv('APEX_PROFILE_URL').format(platform, name), color=0x1364a1)
        for key, value in stats.items():
            print(f'{client.user} has retrieved your Apex stats!')
            if isinstance(stats, dict):
                    embed.add_field(name=value['displayName'], value=value['displayValue'], inline=True)
                    embed.timestamp = datetime.datetime.utcnow()
                    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await interation.response.send_message(embed=embed) 
    else:
        await interation.response.send_message("`!apex <steamid_64>`")

#!lol
@client.tree.command(name="lol", description="Check your LoL Player Stats")
async def lol(interactions: discord.Interaction, *,summoner: str):
    summoner = watcher.summoner.by_name('euw1',summoner)
    stats = watcher.league.by_summoner('euw1', summoner['id'])
    num = 0
    if (stats[0]['queueType'] == 'RANKED_SOLO_5x5'):
        num = 0
    else:
        num = 1
    tier = stats[num]['tier']
    rank = stats[num]['rank']
    lp = stats[num]['leaguePoints']
    wins= int(stats[num]['wins'])
    losses = int(stats[num]['losses'])
    wr = int((wins/(wins+losses))* 100)
    hotStreak = int(stats[num]['hotStreak'])
    level = int(summoner['summonerLevel'])
    icon = int(summoner['profileIconId'])
    embed = discord.Embed(title=f"League of Legends - Player Stats", color=0x1364a1)
    print(f'{client.user} has retrieved your LoL stats!')
    embed.set_thumbnail(url=f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{icon}.jpg")
    embed.add_field(name="Ranked Solo/Duo", value=f'{str(tier)} {str(rank)} {str(lp)} LP \n Winrate: {str(wr)}% \n Winstreak: {str(hotStreak)}')
    embed.add_field(name="Level", value=f'{str(level)}')
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await interactions.response.send_message(embed=embed) 

@client.event
async def p_error(interactions: discord.Interaction, error):
    if isinstance(error,commands.MissingRequiredArguments):
        await interactions.response.send_message('Please specify a summoner name')

client.run(os.getenv('TOKEN'))
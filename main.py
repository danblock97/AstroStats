import datetime
import discord
import os
import json
from discord.ext import commands
import requests
from dotenv import load_dotenv
from riotwatcher import LolWatcher

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix = "!", help_command=None, intents=intents) 

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

#!help
@client.command(pass_context=True,name="help")
async def help(ctx):
    embed=discord.Embed(title="NexusBot", color=0x1364a1)
    embed.add_field(name="CSGO Lifetime Stats", value="`!csgo`")
    embed.add_field(name="Apex Legends Lifetime Stats", value="`!apex`")
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await ctx.channel.send(embed=embed)

#!csgo
@client.command()
async def csgo(ctx, user_identifier=None):
    if user_identifier is None:
        await ctx.send("`!csgo <steamid_64>`")
        return

    # Make the API request
    response = requests.get(os.getenv('CSGO_API_URL').format(user_identifier), headers={"TRN-Api-Key": os.getenv('API_KEY')})

    if response.status_code == 200:
        data = response.json()
        segments = data['data']['segments'][0]
        stats = segments['stats']

        embed = discord.Embed(title=f"CS:GO - Lifetime Overview", url=os.getenv('CSGO_PROFILE_URL').format(user_identifier), color=0x1364a1)
        for key, value in stats.items():
            print(f'{client.user} has retrieved your CSGO stats!')
            if isinstance(stats, dict):
                    embed.add_field(name=value['displayName'], value=value['displayValue'], inline=True)
                    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await ctx.channel.send(embed=embed) 
    else:
        await ctx.send("`!csgo <steamid_64>`")

#!apex
@client.command()
async def apex(ctx, user_identifier=None, platform=None):
    if user_identifier is None:
        await ctx.send("`!apex <steamid_64>`")
        if platform is None:
         await ctx.send("`!apex <platform>`")
        return

    # Make the API request
    response = requests.get(os.getenv('APEX_API_URL').format(platform, user_identifier), headers={"TRN-Api-Key": os.getenv('API_KEY')}) 

    if response.status_code == 200:
        data = response.json()
        segments = data['data']['segments'][0]
        stats = segments['stats']

        embed = discord.Embed(title=f"Apex Legends - Lifetime Overview", url=os.getenv('APEX_PROFILE_URL').format(platform, user_identifier), color=0x1364a1)
        for key, value in stats.items():
            print(f'{client.user} has retrieved your Apex stats!')
            if isinstance(stats, dict):
                    embed.add_field(name=value['displayName'], value=value['displayValue'], inline=True)
                    embed.timestamp = datetime.datetime.utcnow()
                    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await ctx.channel.send(embed=embed) 
    else:
        await ctx.send("`!apex <steamid_64>`")

#!lol
@client.command(aliases=['lolstats'])
async def lol(ctx, *,summonerName):
    summoner = watcher.summoner.by_name('euw1',summonerName)
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
    embed = discord.Embed(title=f"League of Legends - Player Stats", color=0x1364a1)
    print(f'{client.user} has retrieved your LoL stats!')
    embed.add_field(name="Level", value=f'{str(level)}')
    embed.add_field(name="Rank", value=f'{str(tier)} {str(rank)} {str(lp)} LP')
    embed.add_field(name="Winrate", value=f'{str(wr)}%')
    embed.add_field(name="Hot Streak", value=f'{str(hotStreak)}')
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await ctx.channel.send(embed=embed) 

@client.event
async def p_error(ctx, error):
    if isinstance(error,commands.MissingRequiredArguments):
        await ctx.send('Please specify a summoner name')

client.run(os.getenv('TOKEN'))
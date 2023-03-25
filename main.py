import discord
import os
from discord.ext import commands
import requests
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix = "!", help_command=None, intents=intents) 

load_dotenv()

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    try:
        synced = await client.tree.sync()
        print(f"Commands Synced")
    except Exception as e:
        print(e)
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Your Mum"))

#!help
@client.command(pass_context=True,name="help")
async def help(ctx):
    embed=discord.Embed(
        title="NexusBot",
        color=0x1364a1
    )
    embed.add_field(
        name="CSGO Lifetime Stats",
        value="`!csgo`"
    )
    embed.add_field(
    name="Apex Legends Lifetime Stats",
    value="`!apex`"
    )
    await ctx.channel.send(embed=embed)

#!csgo
@client.command()
async def csgo(ctx, user_identifier=None):
    if user_identifier is None:
        await ctx.send("`!csgo <steamid_64>`")
        return

    # Make the API request
    r = requests.get(os.getenv('CSGO_API_URL').format(user_identifier), headers={"TRN-Api-Key": os.getenv('API_KEY')})

    if r.status_code == 200:
        data = r.json()
        segments = data['data']['segments'][0]
        stats = segments['stats']

        embed = discord.Embed(title=f"CS:GO - Lifetime Overview", color=0x1364a1)
        for key, value in stats.items():
            print(f'{client.user} has retrieved your CSGO stats!')
            if isinstance(stats, dict):
                    embed.add_field(name=value['displayName'], value=value['displayValue'], inline=True)
                    embed.set_footer(text="Bot By Goldiez")
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

        embed = discord.Embed(title=f"Apex Legends - Lifetime Overview", color=0x1364a1)
        for key, value in stats.items():
            print(f'{client.user} has retrieved your Apex stats!')
            if isinstance(stats, dict):
                    embed.add_field(name=value['displayName'], value=value['displayValue'], inline=True)
                    embed.set_footer(text="Bot By Goldiez")
        await ctx.channel.send(embed=embed) 
    else:
        await ctx.send("`!apex <steamid_64>`")

client.run(os.getenv('TOKEN'))
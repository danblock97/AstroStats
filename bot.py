import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import logging
from commands import apex, league, fortnite, horoscope, help, review, servers, kick

# Load environment variables
load_dotenv()

# Get the blacklisted guild IDs from the environment variable
blacklisted_guilds = set(map(int, os.getenv('BLACKLISTED_GUILDS', None).split(','))) if os.getenv('BLACKLISTED_GUILDS') else set()


logger = logging.getLogger('discord.gateway')
logger.setLevel(logging.ERROR)  # Maybe fix as server grows

# Create the bot instance
intents = discord.Intents.all()
client = commands.Bot(command_prefix="/", help_command=None, intents=intents)

# Setup command modules
apex.setup(client)
league.setup(client)
fortnite.setup(client)
horoscope.setup(client)
# servers.setup(client)
# kick.setup(client)
help.setup(client)
review.setup(client)

# Event for when the bot is ready
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

    try:
        await client.wait_until_ready()  # Wait until the bot is fully connected
        synced = await client.tree.sync()
        print(f"Commands Synced")
    except Exception as e:
        print(e)

    await update_presence()  # Call the function to set initial presence

# Function to update the bot's presence
async def update_presence():
    while True:
        guild_count = len(client.guilds)
        presence = discord.Activity(type=discord.ActivityType.playing, name=f"on {guild_count} servers")
        await client.change_presence(activity=presence)
        await asyncio.sleep(18000)  # Update every 5 hours

# Event for handling interaction errors
@client.event
async def p_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.MissingRequiredArguments):
        await interaction.response.send_message('Missing required arguments.')

# Event for checking if the guild is blacklisted before joining
@client.event
async def on_guild_join(guild):
    if guild.id in blacklisted_guilds:
        await guild.leave()
        print(f"Left blacklisted guild: {guild.name} ({guild.id})")

# Start the bot
client.run(os.getenv('TOKEN'))

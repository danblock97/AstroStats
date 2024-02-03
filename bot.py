import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import logging
from commands import apex, league, fortnite, horoscope, help, review

# Load environment variables
load_dotenv()

logger = logging.getLogger('discord.gateway')
logger.setLevel(logging.ERROR)  # Maybe fix as server grows

# Create the bot instance
client = commands.Bot(command_prefix="/", help_command=None, intents=discord.Intents.all())

# Setup command modules
apex.setup(client)
league.setup(client)
fortnite.setup(client)
horoscope.setup(client)
help.setup(client)
review.setup(client)

# Event for when the bot is ready
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

# Start the bot
client.run(os.getenv('TOKEN'))

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import logging
from commands import apex, league, fortnite, horoscope, help, review, tft, kick, servers, show_update  # Import the new command
import re
from utils import fetch_star_rating  # Import the function

# Load environment variables
load_dotenv()

# Get the blacklisted guild IDs from the environment variable
blacklisted_guilds = set(map(int, os.getenv('BLACKLISTED_GUILDS', '').split(','))) if os.getenv('BLACKLISTED_GUILDS') else set()

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
tft.setup(client)
help.setup(client)
review.setup(client)
show_update.setup(client)  # Add the new command
# kick.setup(client)
# servers.setup(client)

# Regex pattern to match Discord invite links
invite_link_pattern = re.compile(r"(https?://)?(www\.)?(discord\.gg|discordapp\.com/invite)/[A-Za-z0-9]+")

# Event for when the bot is ready
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

    try:
        await client.wait_until_ready()  # Wait until the bot is fully connected

        # Explicitly sync the commands here
        await client.tree.sync()
        print("Commands Synced")

        print("Bot is ready.")
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

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Check if the message contains a Discord invite link
    if invite_link_pattern.search(message.content):
        await message.channel.send(
            "Need Horoscopes? Apex Stats? Fortnite Stats? LoL Stats? Idk Add me! <https://astrostats.vercel.app>"
        )

    # Check for the specific phrase
    if "Hey, AstroStats, show me your latest update" in message.content:
        ctx = await client.get_context(message)
        await show_update.show_update(ctx)

    await client.process_commands(message)

# Event for handling interaction errors
@client.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingRequiredArguments):
        await ctx.send('Missing required arguments.')

# Event for checking if the guild is blacklisted before joining
@client.event
async def on_guild_join(guild):
    if guild.id in blacklisted_guilds:
        await guild.leave()
        print(f"Left blacklisted guild: {guild.name} ({guild.id})")

# Start the bot
client.run(os.getenv('TOKEN'))

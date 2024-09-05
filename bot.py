import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import logging
import sys  # Import sys module

# Add the 'commands' directory to the system path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'commands'))

# Import command modules from 'commands' directory
from commands import apex, league, fortnite, horoscope, help, review, tft, kick, servers, pet_commands, show_update  # Add show_update here
from league import fetch_application_emojis  # Import the function

# Load environment variables
load_dotenv()

# Get the blacklisted guild IDs from the environment variable
blacklisted_guilds = set(map(int, os.getenv('BLACKLISTED_GUILDS', '').split(','))) if os.getenv('BLACKLISTED_GUILDS') else set()

logger = logging.getLogger('discord.gateway')
logger.setLevel(logging.ERROR)  # Set logging level

# Create the bot instance with only the necessary intents
intents = discord.Intents.default()
client = commands.Bot(command_prefix="/", intents=intents)  # Use commands.Bot to handle slash commands and text commands

# Global dictionary to store emojis
emojis = {}

# Setup command modules (apex, league, etc.)
async def setup_commands():
    await apex.setup(client)
    league.setup(client)
    await fortnite.setup(client)
    await horoscope.setup(client)
    tft.setup(client)
    await help.setup(client)
    review.setup(client)
    pet_commands.setup(client)
    show_update.setup(client)
    await kick.setup(client)
    # await servers.setup(client)

# Event for when the bot is ready
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

    try:
        await client.wait_until_ready()  # Wait until the bot is fully connected

        # Call the setup commands function here to register commands
        await setup_commands()

        # Explicitly sync the commands here
        await client.tree.sync()
        print("Commands Synced")

        # Fetch and store emojis
        global emojis
        emoji_data = await fetch_application_emojis()

        if emoji_data:
            for emoji in emoji_data:
                if isinstance(emoji, dict) and 'name' in emoji and 'id' in emoji:
                    emojis[emoji['name']] = f"<:{emoji['name']}:{emoji['id']}>"
                else:
                    logging.error(f"Unexpected emoji format: {emoji}")

        print("Bot is ready.")
    except Exception as e:
        print(f"Error during on_ready: {e}")

    await update_presence()  # Call the function to set initial presence


# Function to update the bot's presence
async def update_presence():
    while True:
        guild_count = len(client.guilds)
        presence = discord.Activity(type=discord.ActivityType.playing, name=f"on {guild_count} servers")
        await client.change_presence(activity=presence)
        await asyncio.sleep(18000)  # Update every 5 hours

# Event for handling command errors
@client.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        # Ignore CommandNotFound errors
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Missing required arguments.')
    else:
        print(f"Unhandled command error: {error}")

# Event for checking if the guild is blacklisted before joining
@client.event
async def on_guild_join(guild):
    if guild.id in blacklisted_guilds:
        await guild.leave()
        print(f"Left blacklisted guild: {guild.name} ({guild.id})")


# Start the bot
client.run(os.getenv('TOKEN'))

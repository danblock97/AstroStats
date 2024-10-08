import discord
import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get the owner ID and the guild ID (owner's guild) from environment variables
OWNER_ID = int(os.getenv('OWNER_ID'))
OWNER_GUILD_ID = int(os.getenv('OWNER_GUILD_ID'))

# Helper function to handle the kick logic
async def kick_bot_from_guild(interaction: discord.Interaction, guild_id: str):
    try:
        guild = interaction.client.get_guild(int(guild_id))
        if guild:
            await guild.leave()
            await interaction.response.send_message(f"Successfully kicked the bot from the server with ID: {guild_id}")
        else:
            await interaction.response.send_message(f"Error: Server with ID {guild_id} not found.")
    except Exception as e:
        logger.error(f"Error kicking the bot from the server: {e}")
        await interaction.response.send_message(f"Error kicking the bot from the server: {e}")

# Check to ensure the command is only available to the bot owner
def is_owner():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return discord.app_commands.check(predicate)

# Main kick command, only available to the owner
@discord.app_commands.command(name="kick", description="Kick the bot from a specific server (Owner only)")
@is_owner()  # Ensure this command can only be invoked by the owner
async def kick_command(interaction: discord.Interaction, guild_id: str):
    await kick_bot_from_guild(interaction, guild_id)

# Setup function for registering the command (only for the owner's guild)
async def setup(client: discord.Client):
    guild = discord.Object(id=OWNER_GUILD_ID)  # Define the specific guild where the command is visible
    client.tree.add_command(kick_command, guild=guild)

    # Sync only with the owner's guild
    await client.tree.sync(guild=guild)

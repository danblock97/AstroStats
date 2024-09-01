import discord
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get the owner ID from the .env file
OWNER_ID = int(os.getenv('OWNER_ID'))

async def kick(interaction: discord.Interaction, guild_id: str):
    try:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("You do not have permission to use this command.")
            return

        guild = interaction.client.get_guild(int(guild_id))
        if guild:
            await guild.leave()
            await interaction.response.send_message(f"Successfully kicked the bot from the server with ID: {guild_id}")
        else:
            await interaction.response.send_message(f"Error: Server with ID {guild_id} not found.")
    except Exception as e:
        await interaction.response.send_message(f"Error kicking the bot from the server: {e}")

def setup(client):
    @client.tree.command(
        name="kick", description="Kick the bot from a specific server"
    )
    @discord.app_commands.check(lambda interaction: interaction.user.id == OWNER_ID)
    async def kick_server_command(interaction: discord.Interaction, guild_id: str):
        await kick(interaction, guild_id)

    if not client.tree.get_command("kick"):
        client.tree.add_command(kick_server_command)

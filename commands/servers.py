import discord
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get the owner ID from the .env file
OWNER_ID = int(os.getenv('OWNER_ID'))

async def list_servers(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("You do not have permission to use this command.")
        return

    guild_info = [(guild.name, str(guild.id)) for guild in interaction.client.guilds]
    guild_list = "\n".join([f"{name} (ID: {id})" for name, id in guild_info])

    # Specify the file path within the "Documents" directory
    file_path = os.path.join(os.path.expanduser("~"), "Documents", "server_list.txt")

    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(guild_list)
        await interaction.response.send_message(f"Server list saved to `{file_path}`.")
    except Exception as e:
        await interaction.response.send_message(f"Error saving server list: {e}")

def setup(client):
    @client.tree.command(
        name="servers", description="List all servers the bot is in"
    )
    @discord.app_commands.check(lambda interaction: interaction.user.id == OWNER_ID)
    async def list_servers_command(interaction: discord.Interaction):
        await list_servers(interaction)

    if not client.tree.get_command("servers"):
        client.tree.add_command(list_servers_command)

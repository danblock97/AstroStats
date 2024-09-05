import discord
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the owner ID and the guild ID (owner's guild) from environment variables
OWNER_ID = int(os.getenv('OWNER_ID'))
OWNER_GUILD_ID = int(os.getenv('OWNER_GUILD_ID'))

# Helper function to generate and save the list of servers to a file
async def generate_and_save_server_list(interaction: discord.Interaction) -> str:
    guild_info = [(guild.name, str(guild.id)) for guild in interaction.client.guilds]
    guild_list = "\n".join([f"{name} (ID: {id})" for name, id in guild_info])

    # Specify the file path within the "Documents" directory
    file_path = os.path.join(os.path.expanduser("~"), "Documents", "server_list.txt")

    try:
        # Write the guild list to the file
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(guild_list)
        return file_path
    except Exception as e:
        raise RuntimeError(f"Error saving server list: {e}")

# Check to ensure the command is only available to the bot owner
def is_owner():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return discord.app_commands.check(predicate)

# Main list_servers command, restricted to the owner
@is_owner()
async def list_servers_command(interaction: discord.Interaction):
    try:
        # Generate and save the server list
        file_path = await generate_and_save_server_list(interaction)
        # Respond to the owner with the file path
        await interaction.response.send_message(f"Server list saved to `{file_path}`.")
    except Exception as e:
        await interaction.response.send_message(f"Error: {e}")

# Setup function for registering the command (only for the owner's guild)
async def setup(client: discord.Client):
    guild = discord.Object(id=OWNER_GUILD_ID)  # Restrict command to the owner's guild
    client.tree.add_command(
        discord.app_commands.Command(
            name="servers",
            description="List all servers the bot is in (Owner only)",
            callback=list_servers_command
        ),
        guild=guild  # Only available in the owner's guild
    )

    # Sync the command only with the owner's guild
    await client.tree.sync(guild=guild)

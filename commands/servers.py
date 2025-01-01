import os
import discord
from dotenv import load_dotenv

load_dotenv()
OWNER_ID = int(os.getenv('OWNER_ID'))
OWNER_GUILD_ID = int(os.getenv('OWNER_GUILD_ID'))

async def generate_and_save_server_list(interaction: discord.Interaction) -> str:
    guild_info = [(guild.name, str(guild.id)) for guild in interaction.client.guilds]
    guild_list = "\n".join([f"{name} (ID: {id_})" for name, id_ in guild_info])
    file_path = os.path.join(os.path.expanduser("~"), "Documents", "server_list.txt")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(guild_list)
        return file_path
    except Exception as e:
        raise RuntimeError(f"Error saving server list: {e}")

def is_owner():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return discord.app_commands.check(predicate)

@is_owner()
async def list_servers_command(interaction: discord.Interaction):
    try:
        file_path = await generate_and_save_server_list(interaction)
        await interaction.response.send_message(f"Server list saved to `{file_path}`.")
    except Exception as e:
        await interaction.response.send_message(f"Error: {e}")

async def setup(client: discord.Client):
    guild = discord.Object(id=OWNER_GUILD_ID)
    client.tree.add_command(
        discord.app_commands.Command(
            name="servers",
            description="List all servers the bot is in (Owner only)",
            callback=list_servers_command
        ),
        guild=guild
    )
    await client.tree.sync(guild=guild)

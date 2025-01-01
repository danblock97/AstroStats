import os
import logging

import discord
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

OWNER_ID = int(os.getenv('OWNER_ID'))
OWNER_GUILD_ID = int(os.getenv('OWNER_GUILD_ID'))

async def kick_bot_from_guild(interaction: discord.Interaction, guild_id: str):
    try:
        guild = interaction.client.get_guild(int(guild_id))
        if guild:
            await guild.leave()
            await interaction.response.send_message(
                f"Successfully kicked the bot from the server with ID: {guild_id}"
            )
        else:
            await interaction.response.send_message(
                f"Error: Server with ID {guild_id} not found."
            )
    except Exception as e:
        logger.error(f"Error kicking the bot from the server: {e}")
        await interaction.response.send_message(
            f"Error kicking the bot from the server: {e}"
        )

def is_owner():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return discord.app_commands.check(predicate)

@discord.app_commands.command(name="kick", description="Kick the bot from a specific server (Owner only)")
@is_owner()
async def kick_command(interaction: discord.Interaction, guild_id: str):
    await kick_bot_from_guild(interaction, guild_id)

async def setup(client: discord.Client):
    guild = discord.Object(id=OWNER_GUILD_ID)
    client.tree.add_command(kick_command, guild=guild)
    await client.tree.sync(guild=guild)

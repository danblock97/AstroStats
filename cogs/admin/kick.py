import logging
import discord
from discord.ext import commands
from discord import app_commands

from config.settings import OWNER_ID, OWNER_GUILD_ID

logger = logging.getLogger(__name__)

def is_owner():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return app_commands.check(predicate)

@app_commands.command(name="kick", description="Kick the bot from a specific server (Owner only)")
@is_owner()
async def kick_command(interaction: discord.Interaction, guild_id: str):
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

async def setup(client: commands.Bot):
    guild = discord.Object(id=OWNER_GUILD_ID)
    client.tree.add_command(kick_command, guild=guild)
    await client.tree.sync(guild=guild)
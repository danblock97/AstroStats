import discord
from discord import app_commands
from discord.ext import commands

from config.constants import LATEST_UPDATES
from core.utils import get_conditional_embed

class ShowUpdateCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="show_update", description="Show the latest update to AstroStats")
    async def show_update(self, interaction: discord.Interaction):
        # Primary Embed
        embed = discord.Embed(
            title="Latest Bot Updates",
            description=LATEST_UPDATES,
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Support Us ❤️",
            value=(
                "[If you enjoy using this bot, consider supporting us!]"
                "(https://buymeacoffee.com/danblock97)"
            )
        )
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None
        )

        # Fetch Conditional Embed
        conditional_embed = await get_conditional_embed(
            interaction, 'SHOW_UPDATE_EMBED', discord.Color.orange()
        )

        # Prepare Embeds List
        embeds = [embed]
        if conditional_embed:
            embeds.append(conditional_embed)

        # Send the Message with Multiple Embeds
        await interaction.response.send_message(embeds=embeds)

async def setup(bot: commands.Bot):
    await bot.add_cog(ShowUpdateCog(bot))
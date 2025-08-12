import discord
from discord import app_commands
from discord.ext import commands
import os
from config.constants import LATEST_UPDATES
from core.utils import get_conditional_embed
from ui.embeds import create_base_embed, get_premium_promotion_embed

class ShowUpdateCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    @app_commands.command(name="show_update", description="Show the latest update to AstroStats")
    async def show_update(self, interaction: discord.Interaction):
        # Use create_base_embed
        embed = create_base_embed(
            title="Latest Bot Updates",
            description=LATEST_UPDATES,
            color=discord.Color.blue()
        )

        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")

        # Fetch Conditional Embed
        conditional_embed = await get_conditional_embed(
            interaction, 'SHOW_UPDATE_EMBED', discord.Color.orange()
        )

        # Prepare Embeds List
        embeds = [embed]
        if conditional_embed:
            embeds.append(conditional_embed)
        
        # Check if user needs premium promotion
        promo_embed = get_premium_promotion_embed(str(interaction.user.id))
        if promo_embed:
            embeds.append(promo_embed)

        # Send the Message with Multiple Embeds
        await interaction.response.send_message(embeds=embeds)

async def setup(bot: commands.Bot):
    await bot.add_cog(ShowUpdateCog(bot))

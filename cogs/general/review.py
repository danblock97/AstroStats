import discord
from discord import app_commands
from discord.ext import commands
import os
from core.utils import get_conditional_embed
from ui.embeds import create_base_embed, get_premium_promotion_embed

class ReviewCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    @app_commands.command(name="review", description="Leave a review on Top.gg")
    async def review(self, interaction: discord.Interaction):
        # Primary Embed
        embed = create_base_embed(
            title="Enjoying AstroStats?",
            description=(
                "If you're enjoying AstroStats, please consider leaving a review on Top.gg!"
            ),
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Leave a Review",
            value=(
                "[Click here to leave a review on Top.gg]"
                "(https://top.gg/bot/1088929834748616785#reviews)"
            ),
            inline=False
        )
        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")

        # Fetch Conditional Embed
        conditional_embed = await get_conditional_embed(
            interaction, 'REVIEW_EMBED', discord.Color.orange()
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
    await bot.add_cog(ReviewCog(bot))

import discord
from discord import app_commands
from discord.ext import commands

from core.utils import get_conditional_embed

class ReviewCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="review", description="Leave a review on Top.gg")
    async def review(self, interaction: discord.Interaction):
        # Primary Embed
        embed = discord.Embed(
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
        embed.add_field(
            name="Support Us ❤️",
            value=(
                "[If you enjoy using this bot, consider supporting us!]"
                "(https://buymeacoffee.com/danblock97)"
            )
        )

        # Fetch Conditional Embed
        conditional_embed = await get_conditional_embed(
            interaction, 'REVIEW_EMBED', discord.Color.orange()
        )

        # Prepare Embeds List
        embeds = [embed]
        if conditional_embed:
            embeds.append(conditional_embed)

        # Send the Message with Multiple Embeds
        await interaction.response.send_message(embeds=embeds)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReviewCog(bot))
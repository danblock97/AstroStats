import discord
from discord import app_commands
from discord.ext import commands
import os
from core.utils import get_conditional_embed
from ui.embeds import create_base_embed, get_premium_promotion_view


class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    @app_commands.command(name="feedback", description="Submit feedback or feature requests for AstroStats")
    async def feedback_command(self, interaction: discord.Interaction):
        embed = create_base_embed(
            title="💡 Submit Feedback or Feature Requests",
            description=(
                "We value your feedback and ideas! Help shape the future of AstroStats by sharing your suggestions.\n\n"
                "**🆘 Get Support**\n"
                "Share your feedback and feature requests on our support page:\n"
                "[Visit Support Page](https://astrostats.info/support)\n\n"
                "**✨ What to Share**\n"
                "• Detailed description of your feature idea\n"
                "• How it would benefit you and other users\n"
                "• Any specific examples or use cases\n\n"
                "Your feedback helps shape the future of AstroStats!"
            ),
            color=discord.Color.blue()
        )

        conditional_embed = await get_conditional_embed(
            interaction, 'FEEDBACK_EMBED', discord.Color.orange()
        )

        embeds = [embed]
        if conditional_embed:
            embeds.append(conditional_embed)

        premium_view = get_premium_promotion_view(str(interaction.user.id))

        await interaction.response.send_message(embeds=embeds, view=premium_view)

    @app_commands.command(name="bug", description="Report a bug in AstroStats")
    async def bug_command(self, interaction: discord.Interaction):
        embed = create_base_embed(
            title="🐛 Report a Bug",
            description=(
                "Found a bug? Help us fix it quickly by providing detailed information!\n\n"
                "**🆘 Get Support**\n"
                "Report bugs directly on our support page:\n"
                "[Visit Support Page](https://astrostats.info/support)\n\n"
                "**📝 What to Include**\n"
                "• Clear description of the issue\n"
                "• Steps to reproduce the bug\n"
                "• Expected vs. actual behavior\n"
                "• Any error messages or screenshots\n\n"
                "Your reports help us improve the bot's reliability and performance!"
            ),
            color=discord.Color.red()
        )

        conditional_embed = await get_conditional_embed(
            interaction, 'BUG_EMBED', discord.Color.orange()
        )

        embeds = [embed]
        if conditional_embed:
            embeds.append(conditional_embed)

        premium_view = get_premium_promotion_view(str(interaction.user.id))

        await interaction.response.send_message(embeds=embeds, view=premium_view)


async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))

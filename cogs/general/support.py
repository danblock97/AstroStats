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
                "**📝 Submit a Feature Request**\n"
                "Click here to fill out our feature request form:\n"
                "[Submit Feature Request](https://danblock97.atlassian.net/jira/software/c/form/9b68dccf-5be1-4817-b3f5-102b974e025a?atlOrigin=eyJpIjoiZDVkYTQzYTNhYjQ2NGJlNGIxYTk2MTJiMzdhNGVhZmMiLCJwIjoiaiJ9)\n\n"
                "**✨ What to Include**\n"
                "• Detailed description of your feature idea\n"
                "• How it would benefit you and other users\n"
                "• Any specific examples or use cases\n\n"
                "Your feedback helps make AstroStats better for everyone!"
            ),
            color=discord.Color.blue()
        )

        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")
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
                "**📋 Submit a Bug Report**\n"
                "Click here to fill out our bug report form:\n"
                "[Submit Bug Report](https://danblock97.atlassian.net/jira/software/c/form/c31187ff-4e38-40dd-aafd-261adcb7722d?atlOrigin=eyJpIjoiNWJmYjYxYzFmY2VmNDc3YWJhOWE5MzZlYmQ5ZjhmNGYiLCJwIjoiaiJ9)\n\n"
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

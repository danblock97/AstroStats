import discord
from discord import app_commands
from discord.ext import commands
import os
from core.utils import get_conditional_embed
from ui.embeds import create_base_embed # Import create_base_embed


class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    @app_commands.command(name="feedback", description="Submit feedback or feature requests for AstroStats")
    async def feedback_command(self, interaction: discord.Interaction):
        # Use create_base_embed
        embed = create_base_embed(
            title="Submit Feedback or Feature Requests",
            description=(
                "We value your feedback! To submit a feature request or share your thoughts:\\n\\n"
                "**1.** Visit [AstroStats Website](https://astrostats.info)\\n"
                "**2.** Click on the 'Request a Feature' button\\n"
                "**3.** Fill out the form with your suggestion\\n\\n"
                "Alternatively, you can submit feature requests through our [Issue Tracker](https://astrostats.info)\\n\\n"
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

        await interaction.response.send_message(embeds=embeds)

    @app_commands.command(name="bug", description="Report a bug in AstroStats")
    async def bug_command(self, interaction: discord.Interaction):
        # Use create_base_embed
        embed = create_base_embed(
            title="Report a Bug",
            description=(
                "Found a bug? Help us fix it by reporting it directly to the developer:\\n\\n"
                "**1.** Visit [AstroStats Website](https://astrostats.info)\\n"
                "**2.** Click on the 'Report a Bug' button\\n"
                "**3.** Describe the issue in detail (including steps to reproduce)\\n\\n"
                "Alternatively, you can report bugs directly through our [Issue Tracker](https://astrostats.info)\\n\\n"
                "Your reports help us improve the bot's reliability!"
            ),
            color=discord.Color.red()
        )
        # Remove manual footer setting
        # embed.set_footer(
        #     text=f"Requested by {interaction.user.display_name}",
        #     icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None
        # )

        conditional_embed = await get_conditional_embed(
            interaction, 'BUG_EMBED', discord.Color.orange()
        )

        embeds = [embed]
        if conditional_embed:
            embeds.append(conditional_embed)

        await interaction.response.send_message(embeds=embeds)


async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))

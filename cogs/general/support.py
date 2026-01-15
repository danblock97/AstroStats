import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import os
from core.utils import get_conditional_embed
from ui.embeds import create_base_embed, get_premium_promotion_view


class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    @app_commands.command(name="issues", description="View known issues and upcoming features")
    async def issues_command(self, interaction: discord.Interaction):
        embed = create_base_embed(
            title="📋 Issue Tracker & Features",
            description=(
                "Want to see what we're working on? Check out our issue tracker!\n\n"
                "**🔍 Track Progress**\n"
                "View known bugs and upcoming features on our tracking board:\n"
                "[View Issues](https://astrostats.info/issues)\n\n"
                "**✨ What to Look For**\n"
                "• Status of reported bugs\n"
                "• Upcoming feature releases\n"
                "• Planned maintenance\n\n"
                "Stay up to date with the latest development!"
            ),
            color=discord.Color.blue()
        )

        conditional_embed = await get_conditional_embed(
            interaction, 'ISSUES_EMBED', discord.Color.orange()
        )

        embeds = [embed]
        if conditional_embed:
            embeds.append(conditional_embed)

        premium_view = get_premium_promotion_view(str(interaction.user.id))

        await interaction.response.send_message(embeds=embeds, view=premium_view)

    @app_commands.command(name="support", description="Report a bug or request a feature")
    async def support_command(self, interaction: discord.Interaction):
        embed = create_base_embed(
            title="🐛 Report Bugs & Request Features",
            description=(
                "Found a bug or have a great idea? Let us know!\n\n"
                "**🆘 Get Support**\n"
                "Submit reports directly on our support page:\n"
                "[Visit Support Center](https://astrostats.info/support)\n\n"
                "**📝 What to Include**\n"
                "• Clear description of the issue or idea\n"
                "• Steps to reproduce (for bugs)\n"
                "• Screenshots or examples\n\n"
                "Your feedback helps make AstroStats better!"
            ),
            color=discord.Color.red()
        )

        conditional_embed = await get_conditional_embed(
            interaction, 'SUPPORT_EMBED', discord.Color.orange()
        )

        embeds = [embed]
        if conditional_embed:
            embeds.append(conditional_embed)

        premium_view = get_premium_promotion_view(str(interaction.user.id))

        await interaction.response.send_message(embeds=embeds, view=premium_view)

    @app_commands.command(name="invite", description="Get an invite link to add AstroStats")
    async def invite_command(self, interaction: discord.Interaction):
        """Send an invite link for the bot."""
        bot_id = self.bot.user.id if self.bot.user else None
        if not bot_id:
            await interaction.response.send_message(
                "❌ Could not determine bot ID. Please try again shortly.",
                ephemeral=True
            )
            return

        permissions = discord.Permissions(
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True
        )
        invite_url = discord.utils.oauth_url(bot_id, permissions=permissions, scopes=("bot", "applications.commands"))

        embed = create_base_embed(
            title="🔗 Invite AstroStats",
            description=(
                "Add AstroStats to your server and unlock stats, games, and space commands.\n\n"
                f"[Click here to invite]({invite_url})"
            ),
            color=discord.Color.blue()
        )

        view = View()
        view.add_item(Button(label="Invite AstroStats", url=invite_url, style=discord.ButtonStyle.link))

        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))

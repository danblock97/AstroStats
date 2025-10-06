import os
import discord
from discord import app_commands
from discord.ext import commands

from core.utils import get_conditional_embed
from ui.embeds import create_base_embed, get_premium_promotion_view


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    def build_help_embed(self) -> discord.Embed:
        guild_count = len(self.bot.guilds)
        # Use create_base_embed for consistency
        embed = create_base_embed(
            title=f"AstroStats Help & Support - Trusted by {guild_count} servers",
            color=0xdd4f7a
        )
        embed.add_field(
            name="🎮 Gaming Stats Commands",
            value=(
                "**Apex Legends**\n"
                "`/apex <platform> <username>`\n\n"
                "**League of Legends**\n"
                "`/league profile`, `/league championmastery`\n\n"
                "**TFT**\n"
                "`/tft <Summoner#0001>`\n\n"
                "**Fortnite**\n"
                "`/fortnite <time> <name>`"
            ),
            inline=False
        )
        embed.add_field(
            name="🎲 Fun & Games",
            value=(
                "**Horoscope**\n"
                "`/horoscope <sign>`\n\n"
                "**Pet Battles**\n"
                "`/petbattles summon`, `/petbattles battle`, `/petbattles stats`, `/petbattles quests`, `/petbattles achievements`, `/petbattles leaderboard`, `/petbattles vote`\n\n"
                "**Squib Games**\n"
                "`/squibgames start`, `/squibgames run`, `/squibgames status`\n\n"
                "**Catfight PvP**\n"
                "`/catfight @user`, `/catfight-leaderboard`, `/catfight-stats`"
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ Server & Premium",
            value=(
                "**Welcome System** (Admin Only)\n"
                "`/welcome toggle` - Enable/disable welcome messages\n"
                "`/welcome set-message` 🔒 **Premium** - Custom welcome messages\n"
                "`/welcome set-image` 🔒 **Sponsor/VIP** - Custom welcome images\n"
                "`/welcome remove-message`, `/welcome remove-image`, `/welcome test`\n\n"
                "**Premium**\n"
                "`/premium` - View premium features and benefits"
            ),
            inline=False
        )
        embed.add_field(
            name="💬 Support & Feedback",
            value=(
                "`/feedback` - Submit feature requests via Jira form\n"
                "`/bug` - Report bugs via Jira form"
            ),
            inline=False
        )
        embed.add_field(
            name="Check Out My Other Apps",
            value=(
                "[ClutchGG.LOL](https://clutchgg.lol)"
            ),
            inline=False
        )
        embed.add_field(
            name="🆘 Need Help?",
            value=(
                "Use `/bug` to report issues or `/feedback` to suggest features.\n"
                "Both commands link directly to our Jira forms for quick support!\n\n"
                "Visit our [Support Site](https://astrostats.info) for more information."
            ),
            inline=False
        )
        embed.set_footer(text="AstroStats | astrostats.info", icon_url="attachment://astrostats.png")
        return embed

    @app_commands.command(name="help", description="Lists all available commands")
    async def help_command(self, interaction: discord.Interaction):
        main_embed = self.build_help_embed()

        conditional_embed = await get_conditional_embed(interaction, 'HELP_EMBED', discord.Color.orange())
        embeds = [main_embed]
        if conditional_embed:
            embeds.append(conditional_embed)
        
        premium_view = get_premium_promotion_view(str(interaction.user.id))

        await interaction.response.send_message(embeds=embeds, view=premium_view)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))

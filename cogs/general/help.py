﻿import datetime

import discord
from discord import app_commands
from discord.ext import commands

from core.utils import get_conditional_embed


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def build_help_embed(self) -> discord.Embed:
        guild_count = len(self.bot.guilds)
        embed = discord.Embed(
            title=f"AstroStats Help & Support - Trusted by {guild_count} servers",
            color=0xdd4f7a,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(
            name="Commands & Usage",
            value=(
                "**Apex Legends Lifetime Stats**\n"
                "`/apex <platform> <username>`\n\n"
                "**LoL Player Stats**\n"
                "`/league profile`, `/league championmastery`\n\n"
                "**TFT Player Stats**\n"
                "`/tft <Summoner#0001>`\n\n"
                "**Fortnite Player Stats**\n"
                "`/fortnite <time> <name>`\n\n"
                "**Horoscope**\n"
                "`/horoscope <sign>`\n\n"
                "**Pet Battles**\n"
                "`/petbattles summon`, `/petbattles battle`, `/petbattles stats`, `/petbattles quests`, `/petbattles achievements`, `/petbattles leaderboard`, `/petbattles vote`\n\n"
                "**Squib Games**\n"
                "`/squibgames start`, `/squibgames run`, `/squibgames status`"
            ),
            inline=False
        )
        embed.add_field(
            name="Check Out My Other Apps",
            value=(
                "[ClutchGG.LOL](https://clutchgg.lol)\n"
                "[Diverse Diaries](https://diversediaries.com)\n"
                "[SwiftTasks](https://swifttasks.co.uk)"
            ),
            inline=False
        )
        embed.add_field(
            name="Support",
            value="For support please visit [AstroStats](https://astrostats.vercel.app)",
            inline=False
        )
        embed.add_field(
            name="Support Us ❤️",
            value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)",
            inline=False
        )
        embed.set_footer(text="Built By Goldiez ❤️")
        return embed

    @app_commands.command(name="help", description="Lists all available commands")
    async def help_command(self, interaction: discord.Interaction):
        main_embed = self.build_help_embed()

        conditional_embed = await get_conditional_embed(interaction, 'HELP_EMBED', discord.Color.orange())
        embeds = [main_embed]
        if conditional_embed:
            embeds.append(conditional_embed)

        await interaction.response.send_message(embeds=embeds)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
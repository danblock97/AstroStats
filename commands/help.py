import datetime

import discord


def build_help_embed(guild_count: int) -> discord.Embed:
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
            "`/league <Summoner#0001>`\n\n"
            "**TFT Player Stats**\n"
            "`/tft <Summoner#0001>`\n\n"
            "**Fortnite Player Stats**\n"
            "`/fortnite <time> <name>`\n\n"
            "**Horoscope**\n"
            "`/horoscope <sign>`\n\n"
            "**Pet Battles**\n"
            "`/summon_pet`, `/pet_battle`, `/pet_stats`, `/top_pets`"
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


@discord.app_commands.command(name="help", description="Lists all available commands")
async def help(interaction: discord.Interaction):
    guild_count = len(interaction.client.guilds)
    embed = build_help_embed(guild_count)
    await interaction.response.send_message(embed=embed)


async def setup(client: discord.Client):
    client.tree.add_command(help)

import discord
import datetime


async def help(interaction: discord.Interaction):
    guild_count = len(interaction.client.guilds)
    embed = discord.Embed(
        title=f"AstroStats - Trusted by {guild_count} servers", color=0xdd4f7a)
    embed.add_field(name="Apex Legends Lifetime Stats", value="`/apex <username> <xbl/psn/origin>`")
    embed.add_field(name="LoL Player Stats", value="`/profile <summoner name>`")
    embed.add_field(name="Fortnite Player Stats", value="`/fortnite <name>`")
    embed.add_field(name="Horoscope", value="`/horoscope <sign>`")
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez \u2764\uFE0F | Need support? Join our Discord server https://discord.gg/7vxSR9DMF7")
    await interaction.response.send_message(embed=embed)


def setup(client):
    client.tree.command(
        name="help", description="Lists all available commands"
    )(help)

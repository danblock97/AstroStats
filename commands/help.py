import discord
import datetime

async def help(interaction: discord.Interaction):
    guild_count = len(interaction.client.guilds)
    embed = discord.Embed(
        title=f"AstroStats - Trusted by {guild_count} servers", color=0xdd4f7a)
    embed.add_field(name="Apex Legends Lifetime Stats", value="`/apex <platform> <username>`")
    embed.add_field(name="LoL Player Stats", value="`/league <Summoner#0001>`")
    embed.add_field(name="TFT Player Stats", value="`/tft <Summoner#0001>`")
    embed.add_field(name="Fortnite Player Stats", value="`/fortnite <time> <name>`")
    embed.add_field(name="Horoscope", value="`/horoscope <sign>`")
    embed.add_field(name="Pet Battles!", value="`/summon_pet`, `/pet_battle`, `/pet_stats`, `/top_pets`")
    embed.timestamp = datetime.datetime.now(datetime.UTC)
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")
    await interaction.response.send_message(embed=embed)

def setup(client):
    client.tree.command(
        name="help", description="Lists all available commands"
    )(help)

import discord
import datetime

# Helper function to build the help embed
def build_help_embed(guild_count: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"AstroStats Support - Trusted by {guild_count} servers",
        color=0xdd4f7a,
        url="https://astrostats.vercel.app"
    )
    embed.add_field(name="Apex Legends Lifetime Stats", value="`/apex <platform> <username>`")
    embed.add_field(name="LoL Player Stats", value="`/league <Summoner#0001>`")
    embed.add_field(name="TFT Player Stats", value="`/tft <Summoner#0001>`")
    embed.add_field(name="Fortnite Player Stats", value="`/fortnite <time> <name>`")
    embed.add_field(name="Horoscope", value="`/horoscope <sign>`")
    embed.add_field(name="Pet Battles!", value="`/summon_pet`, `/pet_battle`, `/pet_stats`, `/top_pets`")
    embed.add_field(name="Support", value="For support please visit [AstroStats](https://astrostats.vercel.app)")
    embed.add_field(name="Known Issues", value="For all known issues, please visit our [Trello Board](https://trello.com/b/UdZeXlcY/all-known-issues)")
    embed.add_field(name="Support Us ❤️",
                    value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)")
    embed.set_footer(text="Built By Goldiez ❤️")
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    
    return embed

# Main help command
@discord.app_commands.command(name="help", description="Lists all available commands")
async def help(interaction: discord.Interaction):
    guild_count = len(interaction.client.guilds)
    
    # Build the help embed
    embed = build_help_embed(guild_count)
    
    # Send the embed to the interaction response
    await interaction.response.send_message(embed=embed)

# Setup function for the bot
async def setup(client: discord.Client):
    client.tree.add_command(help)

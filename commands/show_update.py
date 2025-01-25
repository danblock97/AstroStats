import discord
from discord import app_commands
from utils.embeds import get_conditional_embed  # Ensure correct import path

LATEST_UPDATES = (
    "**Version 1.7.0**:\n"
    "**🎮 Main Update**\n\n"
    "- **All Commands**\n"
    "  - Added some conditional embeds to show some extra information when there are known issues.\n"
)

async def show_update(interaction: discord.Interaction):
    # Primary Embed
    embed = discord.Embed(
        title="Latest Bot Updates",
        description=LATEST_UPDATES,
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Support Us ❤️",
        value=(
            "[If you enjoy using this bot, consider supporting us!]"
            "(https://buymeacoffee.com/danblock97)"
        )
    )
    embed.set_footer(
        text=f"Requested by {interaction.user.display_name}",
        icon_url=interaction.user.avatar.url
    )
    
    # Fetch Conditional Embed
    conditional_embed = await get_conditional_embed(
        interaction, 'SHOW_UPDATE_EMBED', discord.Color.orange()
    )
    
    # Prepare Embeds List
    embeds = [embed]
    if conditional_embed:
        embeds.append(conditional_embed)
    
    # Send the Message with Multiple Embeds
    await interaction.response.send_message(embeds=embeds)

async def setup(client: discord.Client):
    client.tree.add_command(
        discord.app_commands.Command(
            name="show_update",
            description="Show the latest update to AstroStats",
            callback=show_update
        )
    )

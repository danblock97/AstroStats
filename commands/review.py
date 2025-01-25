import discord
from discord import app_commands

from utils.embeds import get_conditional_embed  # Ensure this import is correct

async def review(interaction: discord.Interaction):
    # Primary Embed
    embed = discord.Embed(
        title="Enjoying AstroStats?",
        description=(
            "If you're enjoying AstroStats, please consider leaving a review on Top.gg!"
        ),
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Leave a Review",
        value=(
            "[Click here to leave a review on Top.gg]"
            "(https://top.gg/bot/1088929834748616785#reviews)"
        ),
        inline=False
    )
    embed.add_field(
        name="Support Us ❤️",
        value=(
            "[If you enjoy using this bot, consider supporting us!]"
            "(https://buymeacoffee.com/danblock97)"
        )
    )

    # Fetch Conditional Embed
    conditional_embed = await get_conditional_embed(
        interaction, 'REVIEW_EMBED', discord.Color.orange()
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
            name="review",
            description="Leave a review on Top.gg",
            callback=review
        )
    )

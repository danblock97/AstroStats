import discord
from discord import app_commands

async def review(interaction: discord.Interaction):
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
    await interaction.response.send_message(embed=embed)

async def setup(client: discord.Client):
    client.tree.add_command(
        discord.app_commands.Command(
            name="review",
            description="Leave a review on top.gg",
            callback=review
        )
    )

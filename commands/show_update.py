import discord

LATEST_UPDATES = (
    "**Version 1.6.3**:\n"
    "**🎮 Main Update**\n\n"
    "- **League of Legends**\n"
    "  - Fixed an issue where Twisted Fate was not showing as a champion icon in the Live Game embed."
    "  - Mel has now been added to AstroStats so will now show in the live game embed."
)

async def show_update(interaction: discord.Interaction):
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
    await interaction.response.send_message(embed=embed)

async def setup(client: discord.Client):
    client.tree.add_command(
        discord.app_commands.Command(
            name="show_update",
            description="Show the latest update to AstroStats",
            callback=show_update
        )
    )

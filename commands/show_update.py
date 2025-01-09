import discord

LATEST_UPDATES = (
    "**Version 1.5.2**:\n"
    "**🎮 Main Updates** 🛠️\n\n"
    "- **Season 15 Assets Update\n"
    "  - We've updated all in-app assets to reflect the changes for League of Legends Season 15. This includes new visuals, champion updates, and other in-game elements to ensure the app stays in sync with the latest season.\n"
    "- **Voting Reminder**:\n"
    "  Remember to use `/vote` every 12 hours on **TOP.GG** to gain XP for your pets!"
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

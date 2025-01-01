import discord

LATEST_UPDATES = (
    "**Version 1.4.4**:\n"
    "**Bug Fixes and Enhancements** 🛠️\n\n"
    "- **Error Handling in Commands**:\n"
    "  - **All Commands**: All commands now have a better error handling system. "
    "If you encounter an error, the bot will now respond with an appropriate embed message.\n\n"
    "- **UI Enhancements**:\n"
    "  - **Improved Readability**: Some commands have been updated to have a better "
    "readability and user experience.\n\n"
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

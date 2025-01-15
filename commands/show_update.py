import discord

LATEST_UPDATES = (
    "**Version 1.6.1**:\n"
    "**🎮 Main Updates** 🛠️\n\n"
    "- **Improved Pet Battles Command Names**\n"
    "  - We've improved the names of all pet battle commands to look a lot cleaner and easier to read! Check out /help for the new command names.\n"
    "- **No need for a Host!**\n"
    "  - We've made sure that a SquibGames session can be started by anyone ensuring you don't need to wait for the host to come back online!\n"
    "- **Squib Game Bugs**\n"
    "  - Squished a couple of bugs found that happened during a SquibGames session!\n"
    "- **Voting Reminder**:\n"
    "  Remember to use `/petbattles vote` every 12 hours on **TOP.GG** to gain XP for your pets!"
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

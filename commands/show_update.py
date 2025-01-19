import discord

LATEST_UPDATES = (
    "**Version 1.6.2**:\n"
    "**🎮 Bug Fix** 🛠️\n\n"
    "- **Resolved Pet Battles Response Error**\n"
    "  - Fixed the issue where the bot would throw a 'Cannot mix embed and embeds' or 'InteractionResponded' error "
    "during pet battles. The commands now properly handle embeds and follow-up messages."
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

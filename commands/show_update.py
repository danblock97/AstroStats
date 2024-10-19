import discord

# Easily editable text for the latest updates
LATEST_UPDATES = """
- **Version 1.4.0**:
  NEW REGION SELECTION & TFT IMPROVEMENTS 🎉

  -**Apex Fixed**: The Apex Command has been fixed after multiple reports of it working 0% of the time! 

  - **Region Selection for League & TFT**: You can now select your region from a dropdown list when using both the League and TFT commands! No need to type it anymore.

  - **TFT Command Enhancements**: The TFT command has been improved to handle errors more gracefully and returns player data even when ranked information is unavailable, similar to the League of Legends command.

  - **Voting for Pet XP**: Remember to use `/vote` every 12 hours to vote for AstroStats on **TOP.GG** and gain XP for your pets!

  - **Minor Fixes**: Various bug fixes and UI improvements to enhance your overall experience.
"""


async def show_update(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Latest Bot Updates",
        description=LATEST_UPDATES,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.avatar.url)
    await interaction.response.send_message(embed=embed)


# Setup function for the bot
async def setup(client: discord.Client):
    client.tree.add_command(
        discord.app_commands.Command(
            name="show_update",
            description="Show the latest update to AstroStats",
            callback=show_update
        )
    )
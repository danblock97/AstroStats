import discord

# Easily editable text for the latest updates
LATEST_UPDATES = """
- **Version 1.4.3**:
  **Bug Fixes and Enhancements** 🛠️

  - **League Command Improvements**:
    - **Missing Champion Icon**: The new champion Ambessa will now show in the Live Game view!

  - **Horoscope Fixes**:
    - **Interaction Failed**: Upon using the Star Rating button, you may find without correct permissions, the bot will return nothing but an 'Interaction Failed'. This has been improved to show you errors via embeds.

  - **Voting Reminder**:
    Remember to use `/vote` every 12 hours on **TOP.GG** to gain XP for your pets!
    
  - **All known issues**:
    For all known issues, please visit our [Trello Board](https://trello.com/b/UdZeXlcY/all-known-issues)
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
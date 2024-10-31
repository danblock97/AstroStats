import discord

# Easily editable text for the latest updates
LATEST_UPDATES = """
- **Version 1.4.1**:
  **Bug Fixes and Enhancements** 🛠️

  - **League Command Improvements**:
    - **Live Game Data Fixes**: Resolved an issue causing a KeyError 'summonerName' when fetching live game data. The bot now correctly retrieves summoner names using PUUIDs.
    - **API Endpoint Update**: Updated the Spectator API endpoint to use v5 and PUUIDs, ensuring accurate and up-to-date live game information.
    - **Champion Icons Update**: Champion icons (emojis) are now displayed to the **left** of champion names for better readability in live game displays.

  - **Horoscope Command Enhancement**:
    - **Interactive Buttons Fix**: Fixed an issue where only the original user could press the "Check Star Rating" button. Now, **any user** can interact with the button to view star ratings.

  - **General Improvements**:
    - **Improved Error Handling**: Enhanced error handling across commands for a smoother user experience.
    - **UI Enhancements**: Minor cosmetic changes have been made to improve the look and feel of bot responses.

  - **Voting Reminder**:
    Remember to use `/vote` every 12 hours on **TOP.GG** to gain XP for your pets!
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
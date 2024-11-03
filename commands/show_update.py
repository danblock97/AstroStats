import discord

# Easily editable text for the latest updates
LATEST_UPDATES = """
- **Version 1.4.2**:
  **Bug Fixes and Enhancements** 🛠️

  - **League Command Improvements**:
    - **Missing Champion Icon**: Resolved an issue where champions such as K'Sante were missing from the icons list.

  - **Apex Fixes**:
    - **No API Key Error**: Resolved an issue where calling the Apex command will result in the bot saying there is no API key. 

  - **Fortnite Fixes**:
    - **Not Well Formatted URL**: Fixed an issue where the Fortnite command can sometimes result in an error about a 'Not Well Formatted URL'.
    - **Ch2 Remix**: The command has been updated to show seasonal stats for Ch2 Remix as of November 3rd. Any games before this will not show.

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
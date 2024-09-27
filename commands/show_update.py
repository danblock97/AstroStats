import discord

# Easily editable text for the latest updates
LATEST_UPDATES = """
- **Version 1.3.0**:
  PET BATTLES: Gain XP Via Daily Voting 🎉

  - **TOP.GG Voting**: You can now use `/vote` every 12 hours to vote for AstroStats and gain XP towards your pet!

  TFT: Minor Fixes

  - **No More Unknown Interactions**: The TFT Command has been implemented with improved error handing to ensure you know the cause of all errors, the command also now returns data even if there is no ranked information. Similar to the League command!
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

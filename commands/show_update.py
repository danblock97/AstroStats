import discord

# Easily editable text for the latest updates
LATEST_UPDATES = """
- **Version 1.3.0**:
  PET BATTLES: Quests and Achievements have been added! 🎉

  - **Daily Quests**: Your pet now receives 3 random daily quests every day at midnight UTC. Complete them to earn extra XP!
  - **Achievements**: Hard-to-reach goals have been introduced. Unlock achievements by accomplishing significant milestones and earn big XP rewards!
  - **Quest Tracking**: Each quest is appropriately tracked with progress bars and notifications upon completion.
  - **New Commands**:
    - `/quests`: View your current daily quests.
    - `/achievements`: View your achievements and progress.
  - **Battle Updates**: Notifications at the end of battles for completed quests and achievements.
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

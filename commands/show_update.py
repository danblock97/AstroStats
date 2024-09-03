import discord

# Easily editable text for the latest updates
LATEST_UPDATES = """
- **Version 1.2.3**:
  Killstreaks and Loss streaks have been added into your pet stats! 
"""

async def show_update(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Latest Bot Updates",
        description=LATEST_UPDATES,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.avatar.url)
    await interaction.response.send_message(embed=embed)

def setup(client):
    client.tree.command(
        name="show_update", description="Show the latest updates to the bot"
    )(show_update)

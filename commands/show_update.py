import discord

# Easily editable text for the latest updates
LATEST_UPDATES = """
- **Version 1.2.3**:
  Introducing Pet Battles!

  Now you can create your own server pet, battle other pets in the server, level up and compete in the leaderboards for the top spot!

  Get started with /help to see all the commands including all related to Pet Battles!

  If you require support, please contact via https://astrostats.vercel.app/
"""

async def show_update(interaction: discord.Interaction):
    print(f"Show Update command called from server ID: {interaction.guild_id}")
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

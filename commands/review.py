import discord

async def review(interaction: discord.Interaction):
    print(f"Review command called from server ID: {interaction.guild_id}")
    review_message = "If you're enjoying AstroStats, please consider leaving a review on Top.gg! " \
                     "https://top.gg/bot/1088929834748616785#reviews"
    await interaction.response.send_message(review_message)

def setup(client):
    client.tree.command(
        name="review", description="Leave a review on Top.gg"
    )(review)

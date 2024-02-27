import discord


async def review(interaction: discord.Interaction):
    review_message = "If you're enjoying AstroStats, please consider leaving a review on Top.gg! " \
                     "https://top.gg/bot/1088929834748616785#reviews"
    await interaction.response.send_message(review_message)


def setup(client):
    client.tree.command(
        name="review", description="Leave a review on Top.gg"
    )(review)

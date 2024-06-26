import requests
from bs4 import BeautifulSoup
import discord

async def fetch_star_rating(interaction: discord.Interaction, sign: str, embed: discord.Embed):
    try:
        await interaction.response.defer()
    except discord.errors.HTTPException:
        # Interaction already acknowledged, do nothing
        pass
    try:
        url = f"https://www.horoscope.com/star-ratings/today/{sign}"
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        star_container = soup.find("div", class_="module-skin")

        if not star_container:
            raise ValueError("Failed to find star rating on the webpage.")

        star_ratings = []
        categories = star_container.find_all("h3")
        for category in categories:
            title = category.text.strip()
            highlight_stars = len(category.find_all("i", class_="icon-star-filled highlight"))
            total_stars = len(category.find_all("i", class_="icon-star-filled"))
            remaining_stars = total_stars - highlight_stars
            stars = '⭐' * highlight_stars + '✩' * remaining_stars
            description = category.find_next("p").text.strip()
            star_ratings.append((title, stars, description))

        rating_text = "\n\n".join([f"{title} {stars}\n{description}" for title, stars, description in star_ratings])

        embed.add_field(name="Star Ratings", value=rating_text, inline=False)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed)

    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        await interaction.followup.send("Sorry, I couldn't retrieve the star rating at the moment. Please try again later.", ephemeral=True)

    except (KeyError, ValueError) as e:
        print(f"Data Error: {e}")
        await interaction.followup.send("Failed to retrieve the star rating. Please ensure you provided a valid zodiac sign and try again.", ephemeral=True)

    except Exception as e:
        print(f"Unexpected Error: {e}")
        await interaction.followup.send("Oops! An unexpected error occurred while processing your request. Please try again later.", ephemeral=True)

import discord
import datetime
import requests
from bs4 import BeautifulSoup
from typing import Literal, Optional

# Zodiac signs and their corresponding data
SIGNS = {
    "aries": {"display": "Aries", "api": 1, "color": 0xC60000},
    "taurus": {"display": "Taurus", "api": 2, "color": 0x179559},
    "gemini": {"display": "Gemini", "api": 3, "color": 0x008080},
    "cancer": {"display": "Cancer", "api": 4, "color": 0xB8C2CA},
    "leo": {"display": "Leo", "api": 5, "color": 0xA12600},
    "virgo": {"display": "Virgo", "api": 6, "color": 0x08470B},
    "libra": {"display": "Libra", "api": 7, "color": 0xEA987F},
    "scorpio": {"display": "Scorpio", "api": 8, "color": 0x004040},
    "sagittarius": {"display": "Sagittarius", "api": 9, "color": 0x64003F},
    "capricorn": {"display": "Capricorn", "api": 10, "color": 0x28251C},
    "aquarius": {"display": "Aquarius", "api": 11, "color": 0x015780},
    "pisces": {"display": "Pisces", "api": 12, "color": 0x598F88},
}

SignLiteral = Literal['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']


# Helper function to fetch the horoscope data from the website
def fetch_horoscope_text(sign: str) -> Optional[str]:
    try:
        url = f"https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx?sign={SIGNS[sign]['api']}"
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        container = soup.find("div", class_="main-horoscope")
        if not container:
            raise ValueError("Failed to find horoscope text on the webpage.")

        horoscope_text = container.find("p").text.strip()
        return horoscope_text

    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return None


# Helper function to fetch the star rating data from the website
async def fetch_star_rating(interaction: discord.Interaction, sign: str, embed: discord.Embed):
    try:
        await interaction.response.defer()  # Acknowledge the interaction to prevent timeout

    except discord.errors.HTTPException:
        pass  # Interaction already acknowledged, do nothing

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
        await interaction.followup.send(
            "Sorry, I couldn't retrieve the star rating at the moment. Please try again later.", ephemeral=True)

    except (KeyError, ValueError) as e:
        print(f"Data Error: {e}")
        await interaction.followup.send(
            "Failed to retrieve the star rating. Please ensure you provided a valid zodiac sign and try again.", ephemeral=True)

    except Exception as e:
        print(f"Unexpected Error: {e}")
        await interaction.followup.send(
            "Oops! An unexpected error occurred while processing your request. Please try again later.", ephemeral=True)


# Helper function to build the horoscope embed
def build_horoscope_embed(sign: str, horoscope_text: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"Horoscope for {SIGNS[sign]['display']}",
        color=SIGNS[sign]['color']
    )
    image_url = f"https://www.horoscope.com/images-US/signs/profile-{sign}.png"
    embed.set_thumbnail(url=image_url)
    embed.add_field(name="Today's Horoscope", value=horoscope_text, inline=False)
    embed.timestamp = datetime.datetime.now(datetime.UTC)
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")
    
    return embed


# Main Horoscope command
async def horoscope(interaction: discord.Interaction, sign: SignLiteral):
    try:
        given_sign = sign.lower()

        if given_sign not in SIGNS:
            raise ValueError("Invalid sign. Please choose a valid zodiac sign.")

        # Fetch the horoscope text
        horoscope_text = fetch_horoscope_text(given_sign)
        if not horoscope_text:
            await interaction.response.send_message(
                "Sorry, I couldn't retrieve the horoscope at the moment. Please try again later."
            )
            return

        # Build the embed with horoscope data
        embed = build_horoscope_embed(given_sign, horoscope_text)

        # Create the button for fetching star ratings
        view = discord.ui.View()
        button = discord.ui.Button(label="Check Star Rating", style=discord.ButtonStyle.primary, custom_id=f"star_rating_{given_sign}")

        async def button_callback(button_interaction: discord.Interaction):
            # Fetch star rating and add it to the embed
            await fetch_star_rating(button_interaction, given_sign, embed)
            # Disable the button after fetching the rating
            button.disabled = True
            button.label = "Star Rating Fetched"
            await button_interaction.message.edit(embed=embed, view=view)

        button.callback = button_callback
        view.add_item(button)

        # Send the embed and button view to the user
        await interaction.response.send_message(embed=embed, view=view)

    except (KeyError, ValueError) as e:
        print(f"Data Error: {e}")
        await interaction.response.send_message(
            "Failed to retrieve the horoscope. Please ensure you provided a valid zodiac sign and try again."
        )

    except Exception as e:
        print(f"Unexpected Error: {e}")
        await interaction.response.send_message(
            "Oops! An unexpected error occurred while processing your request. Please try again later."
        )


# Setup function for the bot
async def setup(client: discord.Client):
    client.tree.add_command(
        discord.app_commands.Command(
            name="horoscope",
            description="Check your Daily Horoscope",
            callback=horoscope
        )
    )

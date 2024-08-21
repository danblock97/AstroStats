import discord
import datetime
import requests
from bs4 import BeautifulSoup
from typing import Literal
from utils import fetch_star_rating  # Use absolute import

signs = {
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

async def horoscope(interaction: discord.Interaction, sign: SignLiteral):
    print(f"Horoscope command called from server ID: {interaction.guild_id}")
    try:
        given_sign = sign.lower()

        if given_sign not in signs:
            raise ValueError("Invalid sign. Please choose a valid zodiac sign.")

        url = "https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx?sign=" + \
              str(signs[given_sign]["api"])

        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        container = soup.find("div", class_="main-horoscope")

        if not container:
            raise ValueError("Failed to find horoscope text on the webpage.")

        horoscope_text = container.find("p").text.strip()

        embed = discord.Embed(title=f"Horoscope for {signs[given_sign]['display']}", color=signs[given_sign]['color'])
        image_url = f"https://www.horoscope.com/images-US/signs/profile-{given_sign}.png"
        embed.set_thumbnail(url=image_url)
        embed.add_field(name="Today's Horoscope", value=horoscope_text, inline=False)
        embed.timestamp = datetime.datetime.now(datetime.UTC)
        embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")

        # Add button to check star rating
        view = discord.ui.View()
        button = discord.ui.Button(label="Check Star Rating", style=discord.ButtonStyle.primary, custom_id=f"star_rating_{given_sign}")

        async def button_callback(button_interaction: discord.Interaction):
            # Fetch star rating
            star_rating_text = await fetch_star_rating(button_interaction, given_sign, embed)
            # Add star rating to the embed
            embed.add_field(name="Star Ratings", value=star_rating_text, inline=False)
            # Disable the button and change its text
            button.disabled = True
            button.label = "Star Rating Fetched"
            # Edit the original message with the updated embed and view
            await button_interaction.message.edit(embed=embed, view=view)

        button.callback = button_callback
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view)

    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Sorry, I couldn't retrieve the horoscope at the moment. Please try again later.")

    except (KeyError, ValueError) as e:
        print(f"Data Error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Failed to retrieve the horoscope. Please ensure you provided a valid zodiac sign and try again.")

    except Exception as e:
        print(f"Unexpected Error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Oops! An unexpected error occurred while processing your request. Please try again later.")

def setup(client):
    client.tree.command(name="horoscope", description="Check your Daily Horoscope")(horoscope)

import discord
import datetime
import requests
from typing import Literal
from bs4 import BeautifulSoup

signs = {
    "aries": {"display": "Aries", "api": 1},
    "taurus": {"display": "Taurus", "api": 2},
    "gemini": {"display": "Gemini", "api": 3},
    "cancer": {"display": "Cancer", "api": 4},
    "leo": {"display": "Leo", "api": 5},
    "virgo": {"display": "Virgo", "api": 6},
    "libra": {"display": "Libra", "api": 7},
    "scorpio": {"display": "Scorpio", "api": 8},
    "sagittarius": {"display": "Sagittarius", "api": 9},
    "capricorn": {"display": "Capricorn", "api": 10},
    "aquarius": {"display": "Aquarius", "api": 11},
    "pisces": {"display": "Pisces", "api": 12},
}

SignLiteral = Literal['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                      'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']


async def horoscope(interaction: discord.Interaction, sign: SignLiteral):
    try:
        given_sign = sign.lower()  # Convert to lowercase to match the URL format

        URL = "https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx?sign=" + \
            str(signs[given_sign]["api"])

        r = requests.get(URL)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, 'html.parser')

        container = soup.find("div", class_="main-horoscope")


        if not container:
            raise ValueError("Failed to find horoscope text on the webpage.")

        horoscope_text = container.find("p").text.strip()

        embed = discord.Embed(title=f"Horoscope for {signs[given_sign]['display']}", color=0xdd4f7a)
        embed.add_field(name="Today's Horoscope", value=horoscope_text, inline=False)
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="Built By Goldiez ❤️")
        await interaction.response.send_message(embed=embed)

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Sorry, I couldn't retrieve the horoscope at the moment. Please try again later.")

    except (KeyError, ValueError) as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Failed to retrieve the horoscope. The service may be currently unavailable.")

    except Exception as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Oops! An unexpected error occurred while processing your request. Please try again later.")

def setup(client):
    client.tree.command(
        name="horoscope", description="Check your Daily Horoscope"
    )(horoscope)

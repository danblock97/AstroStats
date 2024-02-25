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

SignLiteral = Literal['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

async def horoscope(interaction: discord.Interaction, sign: SignLiteral):
    given_sign = sign.lower()  # Convert to lowercase to match the URL format

    URL = "https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx?sign=" + str(signs[given_sign]["api"])

    r = requests.get(URL)
    soup = BeautifulSoup(r.text, 'html.parser')

    container = soup.find("p")

    horoscope_text = container.text.strip()

    embed = discord.Embed(title=f"Horoscope for {signs[given_sign]['display']}", color=0xdd4f7a)
    embed.add_field(name="Today's Horoscope", value=horoscope_text, inline=False)
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await interaction.response.send_message(embed=embed)

def setup(client):
    client.tree.command(name="horoscope", description="Check your Daily Horoscope")(horoscope)

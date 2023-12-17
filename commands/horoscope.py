import discord
import datetime
import requests
from typing import Literal
from bs4 import BeautifulSoup

signs = {
    "aries": 1,
    "taurus": 2,
    "gemini": 3,
    "cancer": 4,
    "leo": 5,
    "virgo": 6,
    "libra": 7,
    "scorpio": 8,
    "sagittarius": 9,
    "capricorn": 10,
    "aquarius": 11,
    "pisces": 12,
}

async def horoscope(interaction: discord.Interaction, sign: Literal['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']):
    print(f"Horoscope command called with sign: {sign}")
    given_sign = sign.lower()  # Convert to lowercase to match the URL format

    URL = "https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx?sign=" + str(signs[given_sign])

    r = requests.get(URL)
    soup = BeautifulSoup(r.text, 'html.parser')

    container = soup.find("p")

    horoscope_text = container.text.strip()

    embed = discord.Embed(title=f"Horoscope for {sign.capitalize()}", color=0xdd4f7a)
    embed.add_field(name="Today's Horoscope", value=horoscope_text, inline=False)
    embed.timestamp = datetime.datetime.utcnow()
    embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
    await interaction.response.send_message(embed=embed)

def setup(client):
    client.tree.command(name="horoscope", description="Check your Daily Horoscope")(horoscope)

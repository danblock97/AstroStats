import datetime
import logging
from typing import Literal, Optional

import aiohttp
import discord
from bs4 import BeautifulSoup

from utils.embeds import get_conditional_embed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

SignLiteral = Literal[
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

async def fetch_horoscope_text(sign: str) -> Optional[str]:
    url = (
        "https://www.horoscope.com/us/horoscopes/general/"
        f"horoscope-general-daily-today.aspx?sign={SIGNS[sign]['api']}"
    )
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    soup = BeautifulSoup(await response.text(), 'html.parser')
                    container = soup.find("div", class_="main-horoscope")
                    if not container:
                        raise ValueError("Failed to find horoscope text on the webpage.")
                    return container.find("p").text.strip()
                elif response.status == 404:
                    return None
                else:
                    logger.error(f"Failed to fetch horoscope for {sign}: HTTP {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Request error while fetching horoscope text for {sign}: {e}", exc_info=True)
            return None

async def fetch_star_rating(sign: str, embed: discord.Embed) -> Optional[discord.Embed]:
    url = f"https://www.horoscope.com/star-ratings/today/{sign}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    soup = BeautifulSoup(await response.text(), 'html.parser')
                    star_container = soup.find("div", class_="module-skin")
                    if not star_container:
                        raise ValueError("Failed to find star rating on the webpage.")

                    star_ratings = []
                    categories = star_container.find_all("h3")
                    for category in categories:
                        title = category.text.strip()
                        highlight_stars = len(
                            category.find_all("i", class_="icon-star-filled highlight")
                        )
                        total_stars = len(category.find_all("i", class_="icon-star-filled"))
                        stars = '⭐' * highlight_stars + '✩' * (total_stars - highlight_stars)
                        description = category.find_next("p").text.strip()
                        star_ratings.append((title, stars, description))

                    rating_text = "\n\n".join(
                        f"**{title}** {stars}\n{description}"
                        for (title, stars, description) in star_ratings
                    )

                    support_us_field = None
                    for i, field in enumerate(embed.fields):
                        if field.name == "Support Us ❤️":
                            support_us_field = field
                            embed.remove_field(i)
                            break

                    embed.add_field(name="Star Ratings", value=rating_text, inline=False)

                    if support_us_field:
                        embed.add_field(
                            name=support_us_field.name,
                            value=support_us_field.value,
                            inline=False
                        )
                    return embed
                elif response.status == 404:
                    return None
                else:
                    logger.error(f"Failed to fetch star rating for {sign}: HTTP {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Request error while fetching star rating for {sign}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error in fetch_star_rating for {sign}: {e}", exc_info=True)
            return None

def build_horoscope_embed(sign: str, horoscope_text: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"Horoscope for {SIGNS[sign]['display']}",
        color=SIGNS[sign]['color']
    )
    image_url = f"https://www.horoscope.com/images-US/signs/profile-{sign}.png"
    embed.set_thumbnail(url=image_url)
    embed.add_field(
        name="Today's Horoscope",
        value=horoscope_text,
        inline=False
    )
    embed.add_field(
        name="Support Us ❤️",
        value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)",
        inline=False
    )
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")
    return embed

@discord.app_commands.command(name="horoscope", description="Check your Daily Horoscope")
async def horoscope(interaction: discord.Interaction, sign: SignLiteral):
    try:
        given_sign = sign.lower()
        if given_sign not in SIGNS:
            raise ValueError(f"Invalid sign provided: {given_sign}")

        await interaction.response.defer()

        text = await fetch_horoscope_text(given_sign)
        if not text:
            error_embed = discord.Embed(
                title="Horoscope Not Available",
                description=(
                    f"Sorry, I couldn't retrieve the horoscope for **{sign}** at the moment. "
                    "Please try again later."
                ),
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)
            return

        embed = build_horoscope_embed(given_sign, text)

        # Fetch and attach star rating immediately
        updated_embed = await fetch_star_rating(given_sign, embed)
        if updated_embed:
            embed = updated_embed

        conditional_embed = await get_conditional_embed(interaction, 'HOROSCOPE_EMBED', discord.Color.orange())
        embeds = [embed]
        if conditional_embed:
            embeds.append(conditional_embed)

        # Send final embed(s)
        await interaction.followup.send(embeds=embeds)
    except Exception as e:
        logger.error(f"An error occurred in /horoscope command: {e}", exc_info=True)
        error_embed = discord.Embed(
            title="Command Error",
            description="An error occurred while executing the /horoscope command. Please try again later.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)

@horoscope.error
async def horoscope_error_handler(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    logger = logging.getLogger(__name__)
    logger.error(f"An error occurred in /horoscope command: {error}", exc_info=True)
    error_embed = discord.Embed(
        title="Command Error",
        description="An error occurred while executing the /horoscope command. Please try again later.",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    error_embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")
    if interaction.response.is_done():
        await interaction.followup.send(embed=error_embed)
    else:
        await interaction.response.send_message(embed=error_embed)

async def on_error(event_method, *args, **kwargs):
    logger = logging.getLogger(__name__)
    logger.exception(f"An error occurred in the event: {event_method}", exc_info=True)

async def setup(client: discord.Client):
    client.tree.add_command(horoscope)
    client.event(on_error)

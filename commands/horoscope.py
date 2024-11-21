import discord
import datetime
import aiohttp
from bs4 import BeautifulSoup
from typing import Literal, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

SignLiteral = Literal[
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

# Helper function to fetch the horoscope data from the website
async def fetch_horoscope_text(sign: str) -> Optional[str]:
    url = f"https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx?sign={SIGNS[sign]['api']}"
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
                    return None  # No need to log 404 errors
                else:
                    logger.error(f"Failed to fetch horoscope for {sign}: {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Request error: {e}")
            return None

# Helper function to fetch the star rating data from the website
async def fetch_star_rating(sign: str, embed: discord.Embed):
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
                        highlight_stars = len(category.find_all("i", class_="icon-star-filled highlight"))
                        total_stars = len(category.find_all("i", class_="icon-star-filled"))
                        stars = '⭐' * highlight_stars + '✩' * (total_stars - highlight_stars)
                        description = category.find_next("p").text.strip()
                        star_ratings.append((title, stars, description))

                    rating_text = "\n\n".join([f"**{title}** {stars}\n{description}" for title, stars, description in star_ratings])
                    embed.add_field(name="Star Ratings", value=rating_text, inline=False)
                    return embed
                else:
                    logger.error(f"Failed to fetch star rating for {sign}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Unexpected error in fetch_star_rating: {e}")
            return None

# Helper function to build the horoscope embed
def build_horoscope_embed(sign: str, horoscope_text: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"Horoscope for {SIGNS[sign]['display']}",
        color=SIGNS[sign]['color']
    )
    image_url = f"https://www.horoscope.com/images-US/signs/profile-{sign}.png"
    embed.set_thumbnail(url=image_url)
    embed.add_field(name="Today's Horoscope", value=horoscope_text, inline=False)
    embed.add_field(name="Support Us ❤️",
                    value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)")
    embed.set_footer(text="Built By Goldiez ❤️")
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")
    return embed

# Main Horoscope command
@discord.app_commands.command(name="horoscope", description="Check your Daily Horoscope")
async def horoscope(interaction: discord.Interaction, sign: SignLiteral):
    try:
        given_sign = sign.lower()

        if given_sign not in SIGNS:
            raise ValueError("Invalid sign. Please choose a valid zodiac sign.")

        # Fetch the horoscope text
        horoscope_text = await fetch_horoscope_text(given_sign)
        if not horoscope_text:
            await interaction.response.send_message(
                "Sorry, I couldn't retrieve the horoscope at the moment. Please try again later."
            )
            return

        # Build the embed with horoscope data
        embed = build_horoscope_embed(given_sign, horoscope_text)

        # Create the button for fetching star ratings
        view = discord.ui.View()
        button = discord.ui.Button(
            label="Check Star Rating",
            style=discord.ButtonStyle.primary,
            custom_id=f"star_rating_{given_sign}"
        )

        async def button_callback(button_interaction: discord.Interaction):
            # Check permissions before proceeding
            permissions = button_interaction.channel.permissions_for(button_interaction.guild.me)
            if not permissions.send_messages or not permissions.read_message_history:
                # Build an embed for the error message
                error_embed = discord.Embed(
                    title="Permission Error",
                    description=(
                        "I lack the necessary permissions to send messages or read message history in this channel."
                    ),
                    color=discord.Color.red()
                )
                error_embed.add_field(
                    name="Need Help?",
                    value=(
                        "If you've set up correct permissions but the issue persists, "
                        "[please report it here](https://github.com/danblock97/AstroStats/issues)."
                    ),
                    inline=False
                )
                await button_interaction.response.send_message(
                    embed=error_embed,
                    ephemeral=True
                )
                return

            # Defer the interaction to acknowledge it
            await button_interaction.response.defer()

            # Fetch star rating and update the embed
            updated_embed = await fetch_star_rating(given_sign, embed)
            if updated_embed:
                # Disable the button after fetching the rating
                button.disabled = True
                button.label = "Star Rating Fetched"
                try:
                    # Attempt to edit the original message
                    await button_interaction.message.edit(embed=updated_embed, view=view)
                except discord.Forbidden:
                    # Bot lacks permissions to edit the message
                    error_embed = discord.Embed(
                        title="Permission Error",
                        description=(
                            "I couldn't edit the original message due to missing permissions."
                        ),
                        color=discord.Color.red()
                    )
                    error_embed.add_field(
                        name="Need Help?",
                        value=(
                            "If you've set up correct permissions but the issue persists, "
                            "[please report it here](https://github.com/danblock97/AstroStats/issues)."
                        ),
                        inline=False
                    )
                    await button_interaction.followup.send(
                        embed=error_embed,
                        ephemeral=True
                    )
                    # Send the updated embed as a new message
                    await button_interaction.followup.send(
                        embed=updated_embed,
                        ephemeral=True
                    )
                except Exception as e:
                    # Handle other exceptions
                    logger.error(f"Error editing message: {e}")
                    error_embed = discord.Embed(
                        title="Unexpected Error",
                        description=(
                            "An unexpected error occurred while updating the horoscope."
                        ),
                        color=discord.Color.red()
                    )
                    error_embed.add_field(
                        name="Need Help?",
                        value=(
                            "If you've set up correct permissions but the issue persists, "
                            "[please report it here](https://github.com/danblock97/AstroStats/issues)."
                        ),
                        inline=False
                    )
                    await button_interaction.followup.send(
                        embed=error_embed,
                        ephemeral=True
                    )
            else:
                # Error fetching star rating
                error_embed = discord.Embed(
                    title="Data Retrieval Error",
                    description=(
                        "Sorry, I couldn't retrieve the star rating at the moment. Please try again later."
                    ),
                    color=discord.Color.red()
                )
                error_embed.add_field(
                    name="Need Help?",
                    value=(
                        "If the issue persists, "
                        "[please report it here](https://github.com/danblock97/AstroStats/issues)."
                    ),
                    inline=False
                )
                await button_interaction.followup.send(
                    embed=error_embed,
                    ephemeral=True
                )

        button.callback = button_callback
        view.add_item(button)

        # Send the embed and button view to the user
        await interaction.response.send_message(embed=embed, view=view)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await interaction.response.send_message(
            "Oops! An unexpected error occurred while processing your request. Please try again later."
        )

# Setup function for the bot
async def setup(client: discord.Client):
    client.tree.add_command(horoscope)

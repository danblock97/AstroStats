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
                        # This is an expected scenario if the page structure changes, so we raise ValueError
                        raise ValueError("Failed to find horoscope text on the webpage.")
                    return container.find("p").text.strip()
                elif response.status == 404:
                    # 404 is fairly normal if the site doesn't have data; log a warning instead of an error
                    logger.warning(f"No horoscope text found for {sign} (404).")
                    return None
                else:
                    logger.error(f"Failed to fetch horoscope for {sign}: HTTP {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Request error while fetching horoscope text for {sign}: {e}", exc_info=True)
            return None


# Helper function to fetch the star rating data from the website
async def fetch_star_rating(sign: str, embed: discord.Embed) -> Optional[discord.Embed]:
    url = f"https://www.horoscope.com/star-ratings/today/{sign}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    soup = BeautifulSoup(await response.text(), 'html.parser')
                    star_container = soup.find("div", class_="module-skin")
                    if not star_container:
                        # This indicates the page structure changed or star ratings not found
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

                    rating_text = "\n\n".join(
                        f"**{title}** {stars}\n{description}"
                        for (title, stars, description) in star_ratings
                    )

                    # 1) Temporarily remove the "Support Us ❤️" field (if present)
                    support_us_field = None
                    for i, field in enumerate(embed.fields):
                        if field.name == "Support Us ❤️":
                            support_us_field = field
                            embed.remove_field(i)
                            break

                    # 2) Add the Star Ratings field
                    embed.add_field(
                        name="Star Ratings",
                        value=rating_text,
                        inline=False
                    )

                    # 3) Re-add the "Support Us ❤️" field at the bottom (if it existed before)
                    if support_us_field:
                        embed.add_field(
                            name=support_us_field.name,
                            value=support_us_field.value,
                            inline=False
                        )

                    return embed
                elif response.status == 404:
                    logger.warning(f"No star rating found for {sign} (404).")
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


# Helper function to build the horoscope embed
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
    # Add "Support Us ❤️" so it's always in the embed initially
    embed.add_field(
        name="Support Us ❤️",
        value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)",
        inline=False
    )
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")
    return embed


# Main Horoscope command
@discord.app_commands.command(name="horoscope", description="Check your Daily Horoscope")
async def horoscope(interaction: discord.Interaction, sign: SignLiteral):
    try:
        # Convert user input to lowercase for dictionary lookup
        given_sign = sign.lower()

        if given_sign not in SIGNS:
            # This is a user input error, raise ValueError to handle it
            raise ValueError(f"Invalid sign provided: {given_sign}")

        # Fetch the horoscope text
        horoscope_text = await fetch_horoscope_text(given_sign)
        if not horoscope_text:
            # If we can't get the text (None), send an embedded error
            error_embed = discord.Embed(
                title="Horoscope Not Available",
                description=(
                    f"Sorry, I couldn't retrieve the horoscope for **{sign}** at the moment. "
                    "Please try again later."
                ),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed)
            return

        # Build the embed with horoscope data
        embed = build_horoscope_embed(given_sign, horoscope_text)

        # Create a button to fetch star ratings
        view = discord.ui.View()
        button = discord.ui.Button(
            label="Check Star Rating",
            style=discord.ButtonStyle.primary,
            custom_id=f"star_rating_{given_sign}"
        )

        async def button_callback(button_interaction: discord.Interaction):
            # Check channel permissions
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

            # Fetch the star rating and update the embed
            updated_embed = await fetch_star_rating(given_sign, embed)
            if updated_embed:
                # Disable the button after fetching the rating
                button.disabled = True
                button.label = "Star Rating Fetched"
                try:
                    # Attempt to edit the original message
                    await button_interaction.message.edit(embed=updated_embed, view=view)
                except discord.Forbidden:
                    # Bot lacks permissions to edit the original message
                    logger.error("Bot is forbidden from editing the original message.", exc_info=True)
                    error_embed = discord.Embed(
                        title="Permission Error",
                        description="I couldn't edit the original message due to missing permissions.",
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
                    await button_interaction.followup.send(embed=error_embed, ephemeral=True)
                    # Send the updated embed as a new message, just so the user sees it
                    await button_interaction.followup.send(embed=updated_embed, ephemeral=True)
                except Exception as e:
                    # Handle other unexpected exceptions
                    logger.error(f"Error editing message for /horoscope star rating: {e}", exc_info=True)
                    error_embed = discord.Embed(
                        title="Unexpected Error",
                        description="An unexpected error occurred while updating the horoscope.",
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
                    await button_interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                # Error or no data returned for star rating
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
                await button_interaction.followup.send(embed=error_embed, ephemeral=True)

        # Assign the callback to the button
        button.callback = button_callback
        view.add_item(button)

        # Send the embed and the button
        await interaction.response.send_message(embed=embed, view=view)

    except ValueError as ve:
        # Log ValueError details to console and send a user-friendly message
        logger.error(f"ValueError in /horoscope: {ve}", exc_info=True)
        error_embed = discord.Embed(
            title="Invalid Input",
            description=str(ve),
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed)

    except Exception as e:
        # Log unexpected errors to console
        logger.error(f"Unexpected error in /horoscope command: {e}", exc_info=True)
        error_embed = discord.Embed(
            title="Unexpected Error",
            description=(
                "Oops! An unexpected error occurred while processing your request. "
                "Please try again later."
            ),
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed)


# Slash-command-specific error handler
@horoscope.error
async def horoscope_error_handler(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    logger.error(f"An error occurred in /horoscope command: {error}", exc_info=True)

    error_embed = discord.Embed(
        title="Command Error",
        description="An error occurred while executing the /horoscope command. Please try again later.",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    error_embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")

    # If we've already responded to this interaction, send a follow-up instead
    if interaction.response.is_done():
        await interaction.followup.send(embed=error_embed)
    else:
        await interaction.response.send_message(embed=error_embed)


# (Optional) Global error handler for non-command events
async def on_error(event_method, *args, **kwargs):
    logger.exception(f"An error occurred in the event: {event_method}", exc_info=True)


# Setup function for the bot
async def setup(client: discord.Client):
    client.tree.add_command(horoscope)
    # If you want to enable the global error handler, register it:
    client.event(on_error)

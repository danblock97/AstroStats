import logging
import datetime
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class AstroStatsError(Exception):
    """Base exception class for AstroStats errors."""
    pass


class APIError(AstroStatsError):
    """Raised when an API call fails."""
    pass


class ResourceNotFoundError(AstroStatsError):
    """Raised when a requested resource is not found."""
    pass


class ValidationError(AstroStatsError):
    """Raised when validation fails."""
    pass


async def send_error_embed(interaction: discord.Interaction, title: str, description: str):
    """Send an error embed for a command failure."""
    embed = discord.Embed(
        title=title,
        description=(
            f"{description}\n\nFor more assistance, visit "
            "[AstroStats Support](https://astrostats.info)"
        ),
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.info")

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)


async def default_command_error_handler(interaction: discord.Interaction, error: Exception):
    """Default error handler for command errors."""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await send_error_embed(
            interaction,
            "Missing Arguments",
            "You need to provide all required arguments for this command."
        )
    elif isinstance(error, ResourceNotFoundError):
        await send_error_embed(
            interaction,
            "Not Found",
            f"The requested resource was not found: {str(error)}"
        )
    elif isinstance(error, APIError):
        await send_error_embed(
            interaction,
            "API Error",
            "There was an error connecting to the external service. Please try again later."
        )
    elif isinstance(error, ValidationError):
        await send_error_embed(
            interaction,
            "Validation Error",
            str(error)
        )
    else:
        logger.error(f"Unhandled command error: {error}", exc_info=True)
        await send_error_embed(
            interaction,
            "Unexpected Error",
            "An unexpected error occurred. Please try again later."
        )


def setup_error_handlers(bot: commands.Bot):
    """Set up global error handlers for the bot."""

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError):
        await default_command_error_handler(ctx, error)

    @bot.event
    async def on_error(event_method, *args, **kwargs):
        logger.exception(f"An error occurred in the event: {event_method}", exc_info=True)
import logging
import discord
from discord.ext import commands
from discord import app_commands
from config.settings import OWNER_ID, OWNER_GUILD_ID

logger = logging.getLogger(__name__)

def is_owner():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return app_commands.check(predicate)

@app_commands.command(name="test-error", description="Trigger a test error for webhook testing (Owner only)")
@app_commands.describe(error_type="Type of error to trigger")
@app_commands.choices(error_type=[
    app_commands.Choice(name="Generic Error", value="generic"),
    app_commands.Choice(name="Exception with Traceback", value="exception"),
    app_commands.Choice(name="Critical Error", value="critical"),
    app_commands.Choice(name="Nested Exception", value="nested"),
    app_commands.Choice(name="Division by Zero", value="division"),
])
@is_owner()
async def test_error_command(interaction: discord.Interaction, error_type: str = "generic"):
    """Test command to trigger different types of errors for webhook testing."""
    await interaction.response.send_message(f"✅ Triggering {error_type} error... Check your webhook channel!", ephemeral=True)
    
    if error_type == "generic":
        logger.error("Test generic error - This is a test error message")
    elif error_type == "exception":
        try:
            raise ValueError("This is a test ValueError exception")
        except Exception:
            logger.error("Test exception error", exc_info=True)
    elif error_type == "critical":
        logger.critical("Test critical error - This is a critical test error")
    elif error_type == "nested":
        try:
            def inner_function():
                raise RuntimeError("Inner function error")
            def outer_function():
                inner_function()
            outer_function()
        except Exception:
            logger.error("Test nested exception error", exc_info=True)
    elif error_type == "division":
        try:
            result = 1 / 0
        except ZeroDivisionError:
            logger.error("Test division by zero error", exc_info=True)
    else:
        logger.error(f"Unknown error type: {error_type}")

async def setup(client: commands.Bot):
    guild = discord.Object(id=OWNER_GUILD_ID)
    client.tree.add_command(
        test_error_command,
        guild=guild
    )
    await client.tree.sync(guild=guild)

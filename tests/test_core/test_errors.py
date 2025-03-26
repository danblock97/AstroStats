import pytest
import discord
from unittest.mock import patch, AsyncMock, MagicMock
from core.errors import (
    AstroStatsError, APIError, ResourceNotFoundError, ValidationError,
    send_error_embed, default_command_error_handler, setup_error_handlers
)
from discord.ext import commands


@pytest.mark.asyncio
async def test_send_error_embed_response_not_done(mock_interaction):
    # Test when interaction.response.is_done() is False
    mock_interaction.response.is_done.return_value = False

    # Call the function
    await send_error_embed(mock_interaction, "Test Error", "This is a test error")

    # Verify the correct method was called
    mock_interaction.response.send_message.assert_called_once()

    # Check the embed properties
    called_with_kwargs = mock_interaction.response.send_message.call_args.kwargs
    embed = called_with_kwargs.get('embed')
    assert embed.title == "Test Error"
    assert "This is a test error" in embed.description
    assert embed.color == discord.Color.red()


@pytest.mark.asyncio
async def test_send_error_embed_response_done(mock_interaction):
    # Test when interaction.response.is_done() is True
    mock_interaction.response.is_done.return_value = True

    # Call the function
    await send_error_embed(mock_interaction, "Test Error", "This is a test error")

    # Verify the correct method was called
    mock_interaction.followup.send.assert_called_once()

    # Check the embed properties
    called_with_kwargs = mock_interaction.followup.send.call_args.kwargs
    embed = called_with_kwargs.get('embed')
    assert embed.title == "Test Error"
    assert "This is a test error" in embed.description
    assert embed.color == discord.Color.red()


@pytest.mark.asyncio
async def test_default_command_error_handler_missing_required_argument(mock_interaction):
    # Create a MissingRequiredArgument error
    param = MagicMock()
    param.name = "test_param"
    error = commands.MissingRequiredArgument(param)

    # Call the handler
    with patch('core.errors.send_error_embed') as mock_send_error:
        await default_command_error_handler(mock_interaction, error)

        # Verify send_error_embed was called with the right arguments
        mock_send_error.assert_called_once()
        assert mock_send_error.call_args.args[0] == mock_interaction
        assert mock_send_error.call_args.args[1] == "Missing Arguments"


@pytest.mark.asyncio
async def test_default_command_error_handler_resource_not_found(mock_interaction):
    # Create a ResourceNotFoundError
    error = ResourceNotFoundError("Test resource")

    # Call the handler
    with patch('core.errors.send_error_embed') as mock_send_error:
        await default_command_error_handler(mock_interaction, error)

        # Verify send_error_embed was called with the right arguments
        mock_send_error.assert_called_once()
        assert mock_send_error.call_args.args[0] == mock_interaction
        assert mock_send_error.call_args.args[1] == "Not Found"
        assert "Test resource" in mock_send_error.call_args.args[2]


@pytest.mark.asyncio
async def test_default_command_error_handler_api_error(mock_interaction):
    # Create an APIError
    error = APIError("API failed")

    # Call the handler
    with patch('core.errors.send_error_embed') as mock_send_error:
        await default_command_error_handler(mock_interaction, error)

        # Verify send_error_embed was called with the right arguments
        mock_send_error.assert_called_once()
        assert mock_send_error.call_args.args[0] == mock_interaction
        assert mock_send_error.call_args.args[1] == "API Error"


@pytest.mark.asyncio
async def test_default_command_error_handler_validation_error(mock_interaction):
    # Create a ValidationError
    error = ValidationError("Invalid input")

    # Call the handler
    with patch('core.errors.send_error_embed') as mock_send_error:
        await default_command_error_handler(mock_interaction, error)

        # Verify send_error_embed was called with the right arguments
        mock_send_error.assert_called_once()
        assert mock_send_error.call_args.args[0] == mock_interaction
        assert mock_send_error.call_args.args[1] == "Validation Error"
        assert "Invalid input" in mock_send_error.call_args.args[2]


@pytest.mark.asyncio
async def test_default_command_error_handler_unexpected_error(mock_interaction):
    # Create a generic Exception
    error = Exception("Unexpected error")

    # Call the handler
    with patch('core.errors.send_error_embed') as mock_send_error, \
            patch('core.errors.logger.error') as mock_logger:
        await default_command_error_handler(mock_interaction, error)

        # Verify logger.error was called
        mock_logger.assert_called_once()

        # Verify send_error_embed was called with the right arguments
        mock_send_error.assert_called_once()
        assert mock_send_error.call_args.args[0] == mock_interaction
        assert mock_send_error.call_args.args[1] == "Unexpected Error"


def test_setup_error_handlers(mock_bot):
    # Call the function
    setup_error_handlers(mock_bot)

    # Verify that event handlers were added to the bot
    assert mock_bot.event.call_count == 2


def test_error_classes():
    # Test AstroStatsError
    error = AstroStatsError("Base error message")
    assert str(error) == "Base error message"

    # Test APIError
    api_error = APIError("API error message")
    assert isinstance(api_error, AstroStatsError)
    assert str(api_error) == "API error message"

    # Test ResourceNotFoundError
    not_found_error = ResourceNotFoundError("Resource not found")
    assert isinstance(not_found_error, AstroStatsError)
    assert str(not_found_error) == "Resource not found"

    # Test ValidationError
    validation_error = ValidationError("Validation failed")
    assert isinstance(validation_error, AstroStatsError)
    assert str(validation_error) == "Validation failed"
import pytest
import discord
from unittest.mock import patch, AsyncMock, MagicMock
from cogs.admin.kick import kick_command, is_owner, setup
from discord.ext import commands
from discord import app_commands


@pytest.fixture
def mock_config():
    return {
        'OWNER_ID': 123456789,
        'OWNER_GUILD_ID': 987654321
    }


@pytest.mark.asyncio
async def test_is_owner_check_owner(mock_interaction, mock_config):
    """Test the is_owner check when the user is the owner."""
    # Setup
    mock_interaction.user.id = mock_config['OWNER_ID']

    # Create the check
    with patch('cogs.admin.kick.OWNER_ID', mock_config['OWNER_ID']):
        check = is_owner()
        result = await check.predicate(mock_interaction)

        # Verify the result
        assert result is True


@pytest.mark.asyncio
async def test_is_owner_check_not_owner(mock_interaction, mock_config):
    """Test the is_owner check when the user is not the owner."""
    # Setup
    mock_interaction.user.id = 999999  # Different from OWNER_ID

    # Create the check
    with patch('cogs.admin.kick.OWNER_ID', mock_config['OWNER_ID']):
        check = is_owner()

        # The check should return False
        result = await check.predicate(mock_interaction)
        assert result is False


@pytest.mark.asyncio
async def test_kick_command_success(mock_interaction, mock_config):
    """Test the kick_command when it successfully kicks the bot from a server."""
    # Setup
    guild_id = "123456"
    guild = MagicMock(spec=discord.Guild)
    guild.leave = AsyncMock()

    mock_interaction.client = MagicMock()
    mock_interaction.client.get_guild.return_value = guild

    # Call the command
    with patch('cogs.admin.kick.logger.error') as mock_logger:
        await kick_command(mock_interaction, guild_id)

        # Verify guild.leave was called
        guild.leave.assert_called_once()

        # Verify response
        mock_interaction.response.send_message.assert_called_once()
        called_with = mock_interaction.response.send_message.call_args.args[0]
        assert f"Successfully kicked the bot from the server with ID: {guild_id}" in called_with

        # Verify logger.error was not called
        mock_logger.assert_not_called()


@pytest.mark.asyncio
async def test_kick_command_guild_not_found(mock_interaction, mock_config):
    """Test the kick_command when the guild is not found."""
    # Setup
    guild_id = "123456"

    mock_interaction.client = MagicMock()
    mock_interaction.client.get_guild.return_value = None

    # Call the command
    await kick_command(mock_interaction, guild_id)

    # Verify response
    mock_interaction.response.send_message.assert_called_once()
    called_with = mock_interaction.response.send_message.call_args.args[0]
    assert f"Error: Server with ID {guild_id} not found" in called_with


@pytest.mark.asyncio
async def test_kick_command_exception(mock_interaction, mock_config):
    """Test the kick_command when an exception occurs."""
    # Setup
    guild_id = "123456"
    error_message = "Test error"

    mock_interaction.client = MagicMock()
    mock_interaction.client.get_guild.side_effect = Exception(error_message)

    # Call the command
    with patch('cogs.admin.kick.logger.error') as mock_logger:
        await kick_command(mock_interaction, guild_id)

        # Verify logger.error was called
        mock_logger.assert_called_once()

        # Verify response
        mock_interaction.response.send_message.assert_called_once()
        called_with = mock_interaction.response.send_message.call_args.args[0]
        assert f"Error kicking the bot from the server: {error_message}" in called_with


@pytest.mark.asyncio
async def test_setup(mock_bot, mock_config):
    """Test the setup function."""
    # Setup
    guild = MagicMock(spec=discord.Object)

    # Mock the discord.Object constructor
    with patch('discord.Object', return_value=guild), \
            patch('cogs.admin.kick.OWNER_GUILD_ID', mock_config['OWNER_GUILD_ID']):
        # Call the setup function
        await setup(mock_bot)

        # Verify discord.Object was created with the right ID
        discord.Object.assert_called_once_with(id=mock_config['OWNER_GUILD_ID'])

        # Verify the command was added to the bot's command tree
        mock_bot.tree.add_command.assert_called_once_with(kick_command, guild=guild)

        # Verify the command tree was synced
        mock_bot.tree.sync.assert_called_once_with(guild=guild)
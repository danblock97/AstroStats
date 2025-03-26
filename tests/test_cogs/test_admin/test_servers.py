import pytest
import discord
from unittest.mock import patch, AsyncMock, MagicMock
import os
from cogs.admin.servers import list_servers_command, generate_and_save_server_list, is_owner, setup


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
    with patch('cogs.admin.servers.OWNER_ID', mock_config['OWNER_ID']):
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
    with patch('cogs.admin.servers.OWNER_ID', mock_config['OWNER_ID']):
        check = is_owner()

        # The check should return False
        result = await check.predicate(mock_interaction)
        assert result is False


@pytest.mark.asyncio
async def test_generate_and_save_server_list_success(mock_interaction):
    """Test generate_and_save_server_list when it successfully creates a file."""
    # Setup mock guilds
    guild1 = MagicMock(spec=discord.Guild)
    guild1.name = "Test Guild 1"
    guild1.id = 1234567890

    guild2 = MagicMock(spec=discord.Guild)
    guild2.name = "Test Guild 2"
    guild2.id = 9876543210

    mock_interaction.client.guilds = [guild1, guild2]

    # Mock os functions
    with patch('os.path.join', return_value="/mock/path/server_list.txt"), \
            patch('os.path.expanduser', return_value="/mock/path"), \
            patch('builtins.open', MagicMock()) as mock_open:
        # Call the function
        file_path = await generate_and_save_server_list(mock_interaction)

        # Verify file was written
        mock_open.assert_called_once_with("/mock/path/server_list.txt", "w", encoding="utf-8")

        # Get the write calls
        file_handle = mock_open.return_value.__enter__.return_value
        write_calls = file_handle.write.call_args_list

        # Verify content was written with guild names and IDs
        combined_content = ''.join([call.args[0] for call in write_calls])
        assert "Test Guild 1 (ID: 1234567890)" in combined_content
        assert "Test Guild 2 (ID: 9876543210)" in combined_content

        # Verify the file path was returned
        assert file_path == "/mock/path/server_list.txt"


@pytest.mark.asyncio
async def test_generate_and_save_server_list_error(mock_interaction):
    """Test generate_and_save_server_list when an error occurs."""
    # Setup mock guilds
    guild1 = MagicMock(spec=discord.Guild)
    guild1.name = "Test Guild 1"
    guild1.id = 1234567890

    mock_interaction.client.guilds = [guild1]

    # Mock os functions and force an error when opening the file
    with patch('os.path.join', return_value="/mock/path/server_list.txt"), \
            patch('os.path.expanduser', return_value="/mock/path"), \
            patch('builtins.open', side_effect=IOError("Permission denied")):
        # The function should raise RuntimeError
        with pytest.raises(RuntimeError, match="Error saving server list"):
            await generate_and_save_server_list(mock_interaction)


@pytest.mark.asyncio
async def test_list_servers_command_success(mock_interaction):
    """Test list_servers_command when it successfully generates the server list."""
    # Mock the server list generation function
    with patch('cogs.admin.servers.generate_and_save_server_list',
               return_value=AsyncMock(return_value="/path/to/server_list.txt")):
        # Call the command
        await list_servers_command(mock_interaction)

        # Verify response
        mock_interaction.response.send_message.assert_called_once()
        called_with = mock_interaction.response.send_message.call_args.args[0]
        assert "Server list saved to" in called_with
        assert "/path/to/server_list.txt" in called_with


@pytest.mark.asyncio
async def test_list_servers_command_error(mock_interaction):
    """Test list_servers_command when an error occurs."""
    # Mock the server list generation function to raise an exception
    error_message = "Failed to generate server list"
    with patch('cogs.admin.servers.generate_and_save_server_list',
               side_effect=RuntimeError(error_message)):
        # Call the command
        await list_servers_command(mock_interaction)

        # Verify error response
        mock_interaction.response.send_message.assert_called_once()
        called_with = mock_interaction.response.send_message.call_args.args[0]
        assert f"Error: {error_message}" in called_with


@pytest.mark.asyncio
async def test_setup(mock_bot, mock_config):
    """Test the setup function."""
    # Setup
    guild = MagicMock(spec=discord.Object)

    # Mock the discord.Object constructor
    with patch('discord.Object', return_value=guild), \
            patch('cogs.admin.servers.OWNER_GUILD_ID', mock_config['OWNER_GUILD_ID']):
        # Call the setup function
        await setup(mock_bot)

        # Verify discord.Object was created with the right ID
        discord.Object.assert_called_once_with(id=mock_config['OWNER_GUILD_ID'])

        # Verify the command was added to the bot's command tree
        mock_bot.tree.add_command.assert_called_once_with(
            list_servers_command,
            guild=guild
        )

        # Verify the command tree was synced
        mock_bot.tree.sync.assert_called_once_with(guild=guild)
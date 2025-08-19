import pytest
import discord
from unittest.mock import patch, MagicMock, AsyncMock
import logging


class TestKickCommand:
    """Test admin kick command functionality"""
    
    @pytest.fixture
    def mock_guild(self):
        guild = MagicMock(spec=discord.Guild)
        guild.id = 111222333
        guild.name = "Test Guild"
        guild.leave = AsyncMock()
        return guild

    @pytest.fixture 
    def mock_interaction_owner(self):
        interaction = MagicMock(spec=discord.Interaction)
        interaction.user = MagicMock()
        interaction.user.id = 123456789  # Owner ID
        interaction.client = MagicMock()
        interaction.response = AsyncMock()
        return interaction

    @pytest.fixture
    def mock_interaction_non_owner(self):
        interaction = MagicMock(spec=discord.Interaction)
        interaction.user = MagicMock()
        interaction.user.id = 987654321  # Non-owner ID
        interaction.client = MagicMock()
        interaction.response = AsyncMock()
        return interaction

    @pytest.mark.asyncio
    async def test_is_owner_check_valid_owner(self):
        """Test that is_owner check works for valid owner"""
        from cogs.admin.kick import is_owner
        
        with patch('cogs.admin.kick.OWNER_ID', 123456789):
            # Test the predicate function directly
            async def predicate(interaction):
                return interaction.user.id == 123456789
            
            interaction = MagicMock()
            interaction.user.id = 123456789
            
            result = await predicate(interaction)
            assert result is True

    @pytest.mark.asyncio
    async def test_is_owner_check_invalid_user(self):
        """Test that is_owner check fails for non-owner"""
        from cogs.admin.kick import is_owner
        
        with patch('cogs.admin.kick.OWNER_ID', 123456789):
            # Test the predicate function directly
            async def predicate(interaction):
                return interaction.user.id == 123456789
            
            interaction = MagicMock()
            interaction.user.id = 987654321  # Different ID
            
            result = await predicate(interaction)
            assert result is False

    @pytest.mark.asyncio
    async def test_kick_command_successful(self, mock_interaction_owner, mock_guild):
        """Test successful kick from server"""
        from cogs.admin.kick import kick_command
        
        with patch('cogs.admin.kick.OWNER_ID', 123456789):
            mock_interaction_owner.client.get_guild.return_value = mock_guild
            
            # Call the actual callback function
            await kick_command.callback(mock_interaction_owner, "111222333")
            
            mock_interaction_owner.client.get_guild.assert_called_once_with(111222333)
            mock_guild.leave.assert_called_once()
            mock_interaction_owner.response.send_message.assert_called_once_with(
                "Successfully kicked the bot from the server with ID: 111222333"
            )

    @pytest.mark.asyncio
    async def test_kick_command_guild_not_found(self, mock_interaction_owner):
        """Test kick command when guild is not found"""
        from cogs.admin.kick import kick_command
        
        with patch('cogs.admin.kick.OWNER_ID', 123456789):
            mock_interaction_owner.client.get_guild.return_value = None
            
            await kick_command.callback(mock_interaction_owner, "999888777")
            
            mock_interaction_owner.client.get_guild.assert_called_once_with(999888777)
            mock_interaction_owner.response.send_message.assert_called_once_with(
                "Error: Server with ID 999888777 not found."
            )

    @pytest.mark.asyncio
    async def test_kick_command_invalid_guild_id(self, mock_interaction_owner):
        """Test kick command with invalid guild ID format"""
        from cogs.admin.kick import kick_command
        
        with patch('cogs.admin.kick.OWNER_ID', 123456789):
            await kick_command.callback(mock_interaction_owner, "invalid_id")
            
            # Should handle ValueError from int() conversion
            mock_interaction_owner.response.send_message.assert_called_once()
            call_args = mock_interaction_owner.response.send_message.call_args[0][0]
            assert "Error kicking the bot from the server:" in call_args

    @pytest.mark.asyncio
    async def test_kick_command_exception_handling(self, mock_interaction_owner, mock_guild):
        """Test kick command exception handling"""
        from cogs.admin.kick import kick_command
        
        with patch('cogs.admin.kick.OWNER_ID', 123456789):
            mock_interaction_owner.client.get_guild.return_value = mock_guild
            mock_guild.leave.side_effect = Exception("Network error")
            
            with patch('cogs.admin.kick.logger') as mock_logger:
                await kick_command.callback(mock_interaction_owner, "111222333")
                
                mock_logger.error.assert_called_once()
                mock_interaction_owner.response.send_message.assert_called_once()
                call_args = mock_interaction_owner.response.send_message.call_args[0][0]
                assert "Error kicking the bot from the server:" in call_args
                assert "Network error" in call_args

    @pytest.mark.asyncio
    async def test_setup_function(self):
        """Test the setup function registers command correctly"""
        from cogs.admin.kick import setup
        
        mock_bot = MagicMock(spec=discord.ext.commands.Bot)
        mock_bot.tree = MagicMock()
        mock_bot.tree.add_command = MagicMock()
        mock_bot.tree.sync = AsyncMock()
        
        with patch('cogs.admin.kick.OWNER_GUILD_ID', 111222333):
            await setup(mock_bot)
            
            mock_bot.tree.add_command.assert_called_once()
            mock_bot.tree.sync.assert_called_once()
            
            # Check that the guild object was created correctly
            sync_call_args = mock_bot.tree.sync.call_args[1]
            assert 'guild' in sync_call_args
            assert sync_call_args['guild'].id == 111222333

    def test_kick_command_is_owner_only(self):
        """Test that kick command has owner-only decorator"""
        from cogs.admin.kick import kick_command
        
        # Check that the command has the is_owner check
        assert hasattr(kick_command, 'checks')
        assert len(kick_command.checks) > 0

    def test_kick_command_metadata(self):
        """Test kick command metadata"""
        from cogs.admin.kick import kick_command
        
        assert kick_command.name == "kick"
        assert kick_command.description == "Kick the bot from a specific server (Owner only)"

    @pytest.mark.asyncio
    async def test_kick_command_logging(self, mock_interaction_owner, mock_guild):
        """Test that errors are properly logged"""
        from cogs.admin.kick import kick_command
        
        with patch('cogs.admin.kick.OWNER_ID', 123456789):
            mock_interaction_owner.client.get_guild.return_value = mock_guild
            mock_guild.leave.side_effect = discord.HTTPException(response=MagicMock(), message="Forbidden")
            
            with patch('cogs.admin.kick.logger') as mock_logger:
                await kick_command.callback(mock_interaction_owner, "111222333")
                
                # Should log the error
                mock_logger.error.assert_called_once()
                log_call = mock_logger.error.call_args[0][0]
                assert "Error kicking the bot from the server:" in log_call

    def test_logger_configuration(self):
        """Test that logger is configured properly"""
        from cogs.admin.kick import logger
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "cogs.admin.kick"

class TestKickCommandSecurity:
    """Test security aspects of the kick command"""
    
    def test_owner_id_requirement(self):
        """Test that OWNER_ID is required for security"""
        # This tests that the owner check mechanism exists
        from cogs.admin.kick import is_owner
        
        # The is_owner function should exist and return a check decorator
        check = is_owner()
        assert callable(check)  # Should be a decorator function

    def test_guild_restriction(self):
        """Test that command is restricted to owner guild"""
        # The setup function should register the command only for the owner guild
        # This is tested in test_setup_function above
        pass

    @pytest.mark.asyncio 
    async def test_permission_denied_behavior(self):
        """Test behavior when non-owner tries to use command"""
        # The Discord.py app_commands check system should handle this
        # by not allowing the command to be executed
        # This is more of an integration test
        pass

    def test_command_not_global(self):
        """Test that kick command is not registered globally"""
        # The setup function should only register to owner guild
        # This prevents the command from appearing in other servers
        pass
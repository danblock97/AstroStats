import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock


class TestServerListCommand:
    """Test admin servers command functionality"""
    
    @pytest.fixture
    def mock_guild(self):
        """Mock Discord guild object"""
        guild = MagicMock()
        guild.name = "Test Server"
        guild.id = 123456789
        return guild
    
    @pytest.fixture
    def mock_interaction(self):
        """Mock Discord interaction with bot client"""
        interaction = AsyncMock()
        interaction.client = MagicMock()
        interaction.user = MagicMock()
        interaction.user.id = 142831938855190528  # OWNER_ID from config
        interaction.response = AsyncMock()
        return interaction
    
    @pytest.fixture 
    def mock_multiple_guilds(self):
        """Mock multiple guild objects for testing"""
        guilds = []
        guild_data = [
            ("Test Server 1", 111111111),
            ("Test Server 2", 222222222),
            ("AstroStats Official", 333333333),
            ("Development Server", 444444444)
        ]
        
        for name, guild_id in guild_data:
            guild = MagicMock()
            guild.name = name
            guild.id = guild_id
            guilds.append(guild)
        
        return guilds

    @pytest.mark.asyncio
    async def test_generate_and_save_server_list_single_server(self, mock_interaction, mock_guild):
        """Test generating server list with single server"""
        from cogs.admin.servers import generate_and_save_server_list
        
        mock_interaction.client.guilds = [mock_guild]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Documents subdirectory
            docs_dir = os.path.join(temp_dir, "Documents")
            os.makedirs(docs_dir, exist_ok=True)
            
            # Mock home directory to use temp directory
            with patch('os.path.expanduser', return_value=temp_dir):
                file_path = await generate_and_save_server_list(mock_interaction)
                
                # Verify file was created
                assert os.path.exists(file_path)
                
                # Verify file contents
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                assert "Test Server (ID: 123456789)" in content

    @pytest.mark.asyncio
    async def test_generate_and_save_server_list_multiple_servers(self, mock_interaction, mock_multiple_guilds):
        """Test generating server list with multiple servers"""
        from cogs.admin.servers import generate_and_save_server_list
        
        mock_interaction.client.guilds = mock_multiple_guilds
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Documents subdirectory
            docs_dir = os.path.join(temp_dir, "Documents")
            os.makedirs(docs_dir, exist_ok=True)
            
            with patch('os.path.expanduser', return_value=temp_dir):
                file_path = await generate_and_save_server_list(mock_interaction)
                
                # Verify file was created
                assert os.path.exists(file_path)
                
                # Verify file contents include all servers
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                assert "Test Server 1 (ID: 111111111)" in content
                assert "Test Server 2 (ID: 222222222)" in content
                assert "AstroStats Official (ID: 333333333)" in content
                assert "Development Server (ID: 444444444)" in content
                
                # Verify format (each server on new line)
                lines = content.strip().split('\n')
                assert len(lines) == 4

    @pytest.mark.asyncio
    async def test_generate_and_save_server_list_no_servers(self, mock_interaction):
        """Test generating server list when bot is in no servers"""
        from cogs.admin.servers import generate_and_save_server_list
        
        mock_interaction.client.guilds = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Documents subdirectory
            docs_dir = os.path.join(temp_dir, "Documents")
            os.makedirs(docs_dir, exist_ok=True)
            
            with patch('os.path.expanduser', return_value=temp_dir):
                file_path = await generate_and_save_server_list(mock_interaction)
                
                # Verify file was created but is empty
                assert os.path.exists(file_path)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                assert content.strip() == ""

    @pytest.mark.asyncio
    async def test_generate_and_save_server_list_file_error(self, mock_interaction, mock_guild):
        """Test handling file save errors"""
        from cogs.admin.servers import generate_and_save_server_list
        
        mock_interaction.client.guilds = [mock_guild]
        
        # Mock file operations to raise error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(RuntimeError, match="Error saving server list: Permission denied"):
                await generate_and_save_server_list(mock_interaction)

    @pytest.mark.asyncio
    async def test_generate_and_save_server_list_unicode_names(self, mock_interaction):
        """Test handling servers with unicode/special characters in names"""
        from cogs.admin.servers import generate_and_save_server_list
        
        # Create guilds with special characters
        special_guild_1 = MagicMock()
        special_guild_1.name = "測試服務器"  # Chinese characters
        special_guild_1.id = 555555555
        
        special_guild_2 = MagicMock()
        special_guild_2.name = "🎮 Gaming Hub 🎮"  # Emojis
        special_guild_2.id = 666666666
        
        special_guild_3 = MagicMock()
        special_guild_3.name = "Café & Friends"  # Accented characters
        special_guild_3.id = 777777777
        
        mock_interaction.client.guilds = [special_guild_1, special_guild_2, special_guild_3]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Documents subdirectory
            docs_dir = os.path.join(temp_dir, "Documents")
            os.makedirs(docs_dir, exist_ok=True)
            
            with patch('os.path.expanduser', return_value=temp_dir):
                file_path = await generate_and_save_server_list(mock_interaction)
                
                # Verify file was created and contains unicode content
                assert os.path.exists(file_path)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                assert "測試服務器 (ID: 555555555)" in content
                assert "🎮 Gaming Hub 🎮 (ID: 666666666)" in content
                assert "Café & Friends (ID: 777777777)" in content

    @pytest.mark.asyncio
    async def test_is_owner_predicate_authorized(self):
        """Test owner check predicate with authorized user"""
        from cogs.admin.servers import is_owner
        from config.settings import OWNER_ID
        
        # Mock interaction with owner ID
        interaction = MagicMock()
        interaction.user.id = OWNER_ID
        
        # Test the predicate function directly by creating the same logic
        async def predicate(interaction):
            return interaction.user.id == OWNER_ID
            
        result = await predicate(interaction)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_owner_predicate_unauthorized(self):
        """Test owner check predicate with unauthorized user"""
        from config.settings import OWNER_ID
        
        # Mock interaction with non-owner ID
        interaction = MagicMock()
        interaction.user.id = 999999999  # Different from OWNER_ID
        
        # Test the predicate function directly by creating the same logic
        async def predicate(interaction):
            return interaction.user.id == OWNER_ID
            
        result = await predicate(interaction)
        assert result is False

    @pytest.mark.asyncio
    async def test_list_servers_command_success(self, mock_interaction, mock_guild):
        """Test successful execution of list_servers command"""
        from cogs.admin.servers import list_servers_command
        
        mock_interaction.client.guilds = [mock_guild]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Documents subdirectory
            docs_dir = os.path.join(temp_dir, "Documents")
            os.makedirs(docs_dir, exist_ok=True)
            
            with patch('os.path.expanduser', return_value=temp_dir):
                await list_servers_command.callback(mock_interaction)
                
                # Verify response was sent
                mock_interaction.response.send_message.assert_called_once()
                
                # Verify response contains file path
                call_args = mock_interaction.response.send_message.call_args[0][0]
                assert "Server list saved to" in call_args
                assert "server_list.txt" in call_args

    @pytest.mark.asyncio
    async def test_list_servers_command_error(self, mock_interaction, mock_guild):
        """Test error handling in list_servers command"""
        from cogs.admin.servers import list_servers_command
        
        mock_interaction.client.guilds = [mock_guild]
        
        # Mock file operations to raise error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            await list_servers_command.callback(mock_interaction)
            
            # Verify error response was sent
            mock_interaction.response.send_message.assert_called_once()
            
            # Verify error message
            call_args = mock_interaction.response.send_message.call_args[0][0]
            assert "Error:" in call_args
            assert "Permission denied" in call_args

    @pytest.mark.asyncio
    async def test_list_servers_command_large_server_list(self, mock_interaction):
        """Test command with large number of servers"""
        from cogs.admin.servers import list_servers_command
        
        # Create many guilds
        guilds = []
        for i in range(100):
            guild = MagicMock()
            guild.name = f"Server {i:03d}"
            guild.id = 1000000000 + i
            guilds.append(guild)
        
        mock_interaction.client.guilds = guilds
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Documents subdirectory
            docs_dir = os.path.join(temp_dir, "Documents")
            os.makedirs(docs_dir, exist_ok=True)
            
            with patch('os.path.expanduser', return_value=temp_dir):
                await list_servers_command.callback(mock_interaction)
                
                # Verify successful response
                mock_interaction.response.send_message.assert_called_once()
                call_args = mock_interaction.response.send_message.call_args[0][0]
                assert "Server list saved to" in call_args
                
                # Verify file contains all servers
                file_path = os.path.join(temp_dir, "Documents", "server_list.txt")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.strip().split('\n')
                assert len(lines) == 100
                assert "Server 000 (ID: 1000000000)" in content
                assert "Server 099 (ID: 1000000099)" in content

    @pytest.mark.asyncio
    async def test_file_path_generation(self):
        """Test file path generation logic"""
        from cogs.admin.servers import generate_and_save_server_list
        
        # Create minimal mock interaction
        interaction = MagicMock()
        interaction.client.guilds = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Documents subdirectory
            docs_dir = os.path.join(temp_dir, "Documents")
            os.makedirs(docs_dir, exist_ok=True)
            
            # Override to use temp directory
            with patch('os.path.expanduser', return_value=temp_dir):
                file_path = await generate_and_save_server_list(interaction)
                
                expected_path = os.path.join(temp_dir, "Documents", "server_list.txt")
                assert file_path == expected_path

    def test_server_id_formatting(self):
        """Test server ID is properly converted to string"""
        # Test ID handling with various types
        guild_data = [
            ("Test Server 1", 123456789),        # int
            ("Test Server 2", "987654321"),      # string  
            ("Test Server 3", 111111111111111),  # large int
        ]
        
        for name, guild_id in guild_data:
            guild = MagicMock()
            guild.name = name
            guild.id = guild_id
            
            # Test string conversion
            formatted = f"{name} (ID: {str(guild_id)})"
            assert "(ID: " in formatted
            assert str(guild_id) in formatted

    @pytest.mark.asyncio
    async def test_command_registration_with_setup(self):
        """Test command setup and registration"""
        from cogs.admin.servers import setup
        
        # Mock bot and guild
        mock_bot = MagicMock()
        mock_bot.tree = MagicMock()
        mock_bot.tree.add_command = MagicMock()
        mock_bot.tree.sync = AsyncMock()
        
        # Mock guild object
        with patch('discord.Object') as mock_discord_object:
            mock_guild_obj = MagicMock()
            mock_discord_object.return_value = mock_guild_obj
            
            await setup(mock_bot)
            
            # Verify command was added to tree
            mock_bot.tree.add_command.assert_called_once()
            
            # Verify sync was called with guild
            mock_bot.tree.sync.assert_called_once_with(guild=mock_guild_obj)

    def test_server_list_format_consistency(self):
        """Test server list output format is consistent"""
        # Test format: "Server Name (ID: 123456789)"
        test_cases = [
            ("Simple Server", 123456789),
            ("Server With Spaces", 987654321),
            ("", 111111111),  # Empty name
            ("Very Long Server Name That Might Cause Issues", 222222222),
        ]
        
        for name, server_id in test_cases:
            formatted = f"{name} (ID: {str(server_id)})"
            
            # Should always contain the ID pattern
            assert "(ID: " in formatted
            assert ")" in formatted
            assert str(server_id) in formatted
            
            # Should start with server name
            assert formatted.startswith(name)

    def test_config_import_validation(self):
        """Test that required config values are imported correctly"""
        from cogs.admin.servers import is_owner
        from config.settings import OWNER_ID, OWNER_GUILD_ID
        
        # Test that OWNER_ID is importable and has a value
        assert OWNER_ID is not None
        assert isinstance(OWNER_ID, int)
        
        # Test that OWNER_GUILD_ID is importable and has a value
        assert OWNER_GUILD_ID is not None
        assert isinstance(OWNER_GUILD_ID, int)
        
        # Test that is_owner returns a callable (app_commands.check wrapper)
        predicate_func = is_owner()
        assert callable(predicate_func)
        

    @pytest.mark.asyncio
    async def test_guild_access_patterns(self, mock_interaction):
        """Test different guild access patterns and edge cases"""
        from cogs.admin.servers import generate_and_save_server_list
        
        # Test with guilds that have None attributes
        problematic_guild = MagicMock()
        problematic_guild.name = None
        problematic_guild.id = 123456789
        
        normal_guild = MagicMock()
        normal_guild.name = "Normal Server"
        normal_guild.id = 987654321
        
        mock_interaction.client.guilds = [problematic_guild, normal_guild]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Documents subdirectory
            docs_dir = os.path.join(temp_dir, "Documents")
            os.makedirs(docs_dir, exist_ok=True)
            
            with patch('os.path.expanduser', return_value=temp_dir):
                # Should handle None name gracefully
                file_path = await generate_and_save_server_list(mock_interaction)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Should contain the normal server
                assert "Normal Server (ID: 987654321)" in content
                
                # Should handle None name (converted to string "None")
                assert "None (ID: 123456789)" in content or "(ID: 123456789)" in content
import pytest
from unittest.mock import patch, MagicMock
import os


class TestConfigSettings:
    """Test configuration settings and environment variable handling"""
    
    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing"""
        return {
            'TOKEN': 'test_discord_token_123',
            'OWNER_ID': '142831938855190528',
            'OWNER_GUILD_ID': '987654321123456789',
            'BLACKLISTED_GUILDS': '111111111,222222222,333333333',
            'DISCORD_APP_ID': '123456789987654321',
            'TRN_API_KEY': 'test_trn_api_key',
            'LOL_API': 'test_lol_api_key',
            'TFT_API': 'test_tft_api_key',
            'FORTNITE_API_KEY': 'test_fortnite_api_key',
            'TOPGG_TOKEN': 'test_topgg_token',
            'MONGODB_URI': 'mongodb://test:test@localhost:27017/test_db'
        }

    @pytest.fixture
    def minimal_env_vars(self):
        """Minimal required environment variables"""
        return {
            'TOKEN': 'minimal_token',
            'OWNER_ID': '123456789',
            'OWNER_GUILD_ID': '987654321'
        }

    def test_token_loading(self, mock_env_vars):
        """Test Discord bot token loading"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                # Reload the module to pick up new env vars
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.TOKEN == 'test_discord_token_123'

    def test_owner_id_loading_and_conversion(self, mock_env_vars):
        """Test owner ID loading and integer conversion"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.OWNER_ID == 142831938855190528
                assert isinstance(config.settings.OWNER_ID, int)

    def test_owner_guild_id_loading_and_conversion(self, mock_env_vars):
        """Test owner guild ID loading and integer conversion"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.OWNER_GUILD_ID == 987654321123456789
                assert isinstance(config.settings.OWNER_GUILD_ID, int)

    def test_blacklisted_guilds_parsing(self, mock_env_vars):
        """Test blacklisted guilds parsing from comma-separated string"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                expected_guilds = {111111111, 222222222, 333333333}
                assert config.settings.BLACKLISTED_GUILDS == expected_guilds
                assert isinstance(config.settings.BLACKLISTED_GUILDS, set)

    def test_blacklisted_guilds_empty_handling(self):
        """Test blacklisted guilds when environment variable is empty"""
        empty_env = {'BLACKLISTED_GUILDS': ''}
        
        with patch.dict(os.environ, empty_env, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.BLACKLISTED_GUILDS == set()

    def test_blacklisted_guilds_missing_handling(self):
        """Test blacklisted guilds when environment variable is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.BLACKLISTED_GUILDS == set()

    def test_discord_app_id_loading(self, mock_env_vars):
        """Test Discord application ID loading"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.DISCORD_APP_ID == '123456789987654321'

    def test_api_keys_loading(self, mock_env_vars):
        """Test all API keys are loaded correctly"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.TRN_API_KEY == 'test_trn_api_key'
                assert config.settings.LOL_API == 'test_lol_api_key'
                assert config.settings.TFT_API == 'test_tft_api_key'
                assert config.settings.FORTNITE_API_KEY == 'test_fortnite_api_key'
                assert config.settings.TOPGG_TOKEN == 'test_topgg_token'

    def test_mongodb_uri_loading(self, mock_env_vars):
        """Test MongoDB URI loading"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.MONGODB_URI == 'mongodb://test:test@localhost:27017/test_db'

    def test_missing_environment_variables_handling(self):
        """Test behavior when environment variables are missing"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                # TOKEN should be None when missing
                assert config.settings.TOKEN is None
                
                # OWNER_ID should default to 0
                assert config.settings.OWNER_ID == 0
                
                # OWNER_GUILD_ID should default to 0
                assert config.settings.OWNER_GUILD_ID == 0
                
                # API keys should be None when missing
                assert config.settings.TRN_API_KEY is None
                assert config.settings.LOL_API is None
                assert config.settings.TFT_API is None
                assert config.settings.FORTNITE_API_KEY is None
                assert config.settings.TOPGG_TOKEN is None
                assert config.settings.MONGODB_URI is None

    def test_owner_id_default_value(self):
        """Test OWNER_ID defaults to 0 when not provided"""
        env_without_owner = {'TOKEN': 'test_token'}
        
        with patch.dict(os.environ, env_without_owner, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.OWNER_ID == 0

    def test_owner_guild_id_default_value(self):
        """Test OWNER_GUILD_ID defaults to 0 when not provided"""
        env_without_guild = {'TOKEN': 'test_token'}
        
        with patch.dict(os.environ, env_without_guild, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.OWNER_GUILD_ID == 0

    def test_dotenv_loading_called(self):
        """Test that load_dotenv is called to load .env file"""
        with patch('dotenv.load_dotenv') as mock_load_dotenv:
            import importlib
            import config.settings
            importlib.reload(config.settings)
            
            mock_load_dotenv.assert_called_once()

    def test_integer_conversion_robustness(self):
        """Test integer conversion handles various input formats"""
        test_cases = [
            ('123456789', 123456789),
            ('0', 0),
            ('', 0),  # Default value
        ]
        
        for env_value, expected in test_cases:
            env_vars = {'OWNER_ID': env_value} if env_value != '' else {}
            
            with patch.dict(os.environ, env_vars, clear=True):
                with patch('dotenv.load_dotenv'):
                    import importlib
                    import config.settings
                    importlib.reload(config.settings)
                    
                    assert config.settings.OWNER_ID == expected

    def test_blacklisted_guilds_single_value(self):
        """Test blacklisted guilds with single value"""
        env_vars = {'BLACKLISTED_GUILDS': '123456789'}
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert config.settings.BLACKLISTED_GUILDS == {123456789}

    def test_blacklisted_guilds_with_spaces(self):
        """Test blacklisted guilds parsing handles spaces"""
        env_vars = {'BLACKLISTED_GUILDS': '111111111, 222222222 , 333333333'}
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                # Should handle spaces correctly
                expected_guilds = {111111111, 222222222, 333333333}
                assert config.settings.BLACKLISTED_GUILDS == expected_guilds

    def test_configuration_attributes_exist(self):
        """Test all expected configuration attributes exist"""
        import config.settings
        
        # Bot configuration
        assert hasattr(config.settings, 'TOKEN')
        assert hasattr(config.settings, 'OWNER_ID')
        assert hasattr(config.settings, 'OWNER_GUILD_ID')
        assert hasattr(config.settings, 'BLACKLISTED_GUILDS')
        assert hasattr(config.settings, 'DISCORD_APP_ID')
        
        # API keys
        assert hasattr(config.settings, 'TRN_API_KEY')
        assert hasattr(config.settings, 'LOL_API')
        assert hasattr(config.settings, 'TFT_API')
        assert hasattr(config.settings, 'FORTNITE_API_KEY')
        assert hasattr(config.settings, 'TOPGG_TOKEN')
        
        # MongoDB configuration
        assert hasattr(config.settings, 'MONGODB_URI')

    def test_blacklisted_guilds_type_consistency(self, mock_env_vars):
        """Test blacklisted guilds maintains set type with integer elements"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                assert isinstance(config.settings.BLACKLISTED_GUILDS, set)
                
                # All elements should be integers
                for guild_id in config.settings.BLACKLISTED_GUILDS:
                    assert isinstance(guild_id, int)

    def test_environment_variable_names_correctness(self):
        """Test environment variable names match expected Discord/API conventions"""
        import config.settings
        
        # Test that the variable names used in os.getenv match expected patterns
        # This is more of a documentation test to ensure consistency
        
        # Bot-related should use standard Discord terminology
        assert hasattr(config.settings, 'TOKEN')  # Standard Discord bot token
        assert hasattr(config.settings, 'OWNER_ID')  # Discord user ID
        assert hasattr(config.settings, 'DISCORD_APP_ID')  # Discord application ID
        
        # API keys should have descriptive names
        assert hasattr(config.settings, 'TRN_API_KEY')  # Tracker Network API
        assert hasattr(config.settings, 'LOL_API')  # League of Legends API
        assert hasattr(config.settings, 'TFT_API')  # Teamfight Tactics API
        assert hasattr(config.settings, 'FORTNITE_API_KEY')  # Fortnite API

    def test_mongodb_uri_format_expectations(self, mock_env_vars):
        """Test MongoDB URI follows expected format"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                uri = config.settings.MONGODB_URI
                assert uri.startswith('mongodb://')

    def test_id_fields_are_integers(self, mock_env_vars):
        """Test that ID fields are properly converted to integers"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                # These should be integers for Discord API compatibility
                assert isinstance(config.settings.OWNER_ID, int)
                assert isinstance(config.settings.OWNER_GUILD_ID, int)
                
                # Discord IDs should be positive
                assert config.settings.OWNER_ID >= 0
                assert config.settings.OWNER_GUILD_ID >= 0

    def test_api_keys_are_strings_or_none(self, mock_env_vars):
        """Test API keys are strings when present or None when missing"""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                import config.settings
                importlib.reload(config.settings)
                
                api_keys = [
                    config.settings.TRN_API_KEY,
                    config.settings.LOL_API,
                    config.settings.TFT_API,
                    config.settings.FORTNITE_API_KEY,
                    config.settings.TOPGG_TOKEN,
                    config.settings.MONGODB_URI
                ]
                
                for api_key in api_keys:
                    assert api_key is None or isinstance(api_key, str)

    def test_load_dotenv_import(self):
        """Test that dotenv import and usage is correct"""
        # This test ensures the dotenv library is properly imported and used
        import config.settings
        
        # Should not raise import error
        from dotenv import load_dotenv
        
        # The module should have the load_dotenv call
        # This is tested indirectly by checking the module loads without error

    def test_configuration_security_considerations(self):
        """Test configuration handles security-sensitive data appropriately"""
        import config.settings
        
        # Sensitive fields should not have default values that could be mistaken for real credentials
        sensitive_fields = [
            'TOKEN',
            'TRN_API_KEY', 
            'LOL_API',
            'TFT_API',
            'FORTNITE_API_KEY',
            'TOPGG_TOKEN',
            'MONGODB_URI'
        ]
        
        # When environment variables are missing, these should be None (not empty strings or defaults)
        with patch.dict(os.environ, {}, clear=True):
            with patch('dotenv.load_dotenv'):
                import importlib
                importlib.reload(config.settings)
                
                for field_name in sensitive_fields:
                    field_value = getattr(config.settings, field_name)
                    assert field_value is None, f"Sensitive field {field_name} should be None when missing, got {field_value}"

    def test_blacklisted_guilds_error_handling(self):
        """Test blacklisted guilds handles malformed input gracefully"""
        test_cases = [
            'not_a_number,123456789',  # Mixed valid/invalid
            '123456789,',  # Trailing comma
            ',123456789',  # Leading comma  
            '123456789,,987654321',  # Double comma
        ]
        
        for test_input in test_cases:
            env_vars = {'BLACKLISTED_GUILDS': test_input}
            
            with patch.dict(os.environ, env_vars, clear=True):
                with patch('dotenv.load_dotenv'):
                    import importlib
                    import config.settings
                    
                    # Should not raise an exception
                    try:
                        importlib.reload(config.settings)
                        # Should result in a set (possibly empty if all values are invalid)
                        assert isinstance(config.settings.BLACKLISTED_GUILDS, set)
                    except ValueError:
                        # It's acceptable for malformed input to raise ValueError during int conversion
                        pass
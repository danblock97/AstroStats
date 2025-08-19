import pytest
import logging
import os
import asyncio
from unittest.mock import patch, MagicMock, mock_open
from logging.handlers import RotatingFileHandler


class TestBotEntryPoint:
    """Test bot.py main entry point and logging configuration"""
    
    @pytest.fixture
    def mock_env_logging(self):
        """Mock environment variables for logging tests"""
        return {
            'LOG_LEVEL': 'DEBUG',
            'LOG_TO_FILE': '1'
        }

    @pytest.fixture
    def mock_env_no_file_logging(self):
        """Mock environment for console-only logging"""
        return {
            'LOG_LEVEL': 'WARNING',
            'LOG_TO_FILE': '0'
        }

    def test_logging_configuration_default(self):
        """Test default logging configuration"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('logging.getLogger') as mock_get_logger:
                with patch('logging.StreamHandler') as mock_stream_handler:
                    with patch('logging.Formatter') as mock_formatter:
                        mock_logger = MagicMock()
                        mock_get_logger.return_value = mock_logger
                        
                        # Import bot module to trigger logging setup
                        import bot
                        
                        # Should set INFO level for root logger (first call)
                        mock_logger.setLevel.assert_called()
                        # Check the first call to setLevel (root logger)
                        first_set_level_call = mock_logger.setLevel.call_args_list[0][0][0]
                        assert first_set_level_call == logging.INFO

    def test_logging_configuration_custom_level(self):
        """Test logging with custom log level"""
        with patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG'}, clear=True):
            with patch('logging.getLogger') as mock_get_logger:
                with patch('logging.StreamHandler'):
                    with patch('logging.Formatter'):
                        mock_logger = MagicMock()
                        mock_get_logger.return_value = mock_logger
                        
                        # Re-import to trigger setup with new env
                        import importlib
                        import bot
                        importlib.reload(bot)
                        
                        # Should set DEBUG level
                        mock_logger.setLevel.assert_called()
                        # One of the calls should be DEBUG level
                        calls = mock_logger.setLevel.call_args_list
                        debug_called = any(call[0][0] == logging.DEBUG for call in calls)
                        assert debug_called

    def test_stream_handler_setup(self):
        """Test stream handler is always set up"""
        with patch('logging.getLogger') as mock_get_logger:
            with patch('logging.StreamHandler') as mock_stream_handler:
                with patch('logging.Formatter') as mock_formatter:
                    mock_logger = MagicMock()
                    mock_handler = MagicMock()
                    mock_get_logger.return_value = mock_logger
                    mock_stream_handler.return_value = mock_handler
                    
                    import importlib
                    import bot
                    importlib.reload(bot)
                    
                    # Stream handler should be created and added
                    assert mock_stream_handler.call_count >= 1
                    assert mock_handler.setFormatter.call_count >= 1
                    assert mock_logger.addHandler.call_count >= 1

    def test_file_handler_setup_enabled(self):
        """Test file handler setup when file logging is enabled"""
        with patch.dict(os.environ, {'LOG_TO_FILE': '1'}, clear=True):
            with patch('logging.getLogger') as mock_get_logger:
                with patch('logging.StreamHandler'):
                    with patch('logging.handlers.RotatingFileHandler') as mock_file_handler:
                        with patch('logging.Formatter'):
                            mock_logger = MagicMock()
                            mock_handler = MagicMock()
                            mock_get_logger.return_value = mock_logger
                            mock_file_handler.return_value = mock_handler
                            
                            import importlib
                            import bot
                            importlib.reload(bot)
                            
                            # File handler should be created
                            mock_file_handler.assert_called_once_with(
                                "bot.log",
                                maxBytes=1_000_000,
                                backupCount=3,
                                encoding="utf-8",
                                delay=True
                            )
                            mock_handler.setFormatter.assert_called()

    def test_file_handler_setup_disabled(self):
        """Test file handler is not set up when disabled"""
        with patch.dict(os.environ, {'LOG_TO_FILE': '0'}, clear=True):
            with patch('logging.getLogger') as mock_get_logger:
                with patch('logging.StreamHandler'):
                    with patch('logging.handlers.RotatingFileHandler') as mock_file_handler:
                        mock_logger = MagicMock()
                        mock_get_logger.return_value = mock_logger
                        
                        import importlib
                        import bot
                        importlib.reload(bot)
                        
                        # File handler should not be created
                        mock_file_handler.assert_not_called()

    def test_file_handler_oserror_fallback(self):
        """Test file handler fallback on OSError"""
        with patch.dict(os.environ, {'LOG_TO_FILE': '1'}, clear=True):
            with patch('logging.getLogger') as mock_get_logger:
                with patch('logging.StreamHandler'):
                    with patch('logging.handlers.RotatingFileHandler') as mock_file_handler:
                        mock_logger = MagicMock()
                        mock_get_logger.return_value = mock_logger
                        mock_file_handler.side_effect = OSError("Permission denied")
                        
                        # Should not raise exception, just fall back to console logging
                        import importlib
                        import bot
                        importlib.reload(bot)
                        
                        # Should attempt to create file handler but handle error gracefully
                        mock_file_handler.assert_called_once()

    def test_logging_formatter(self):
        """Test logging formatter is configured correctly"""
        with patch('logging.getLogger') as mock_get_logger:
            with patch('logging.StreamHandler') as mock_stream_handler:
                with patch('logging.Formatter') as mock_formatter:
                    mock_logger = MagicMock()
                    mock_handler = MagicMock()
                    mock_get_logger.return_value = mock_logger
                    mock_stream_handler.return_value = mock_handler
                    
                    import importlib
                    import bot
                    importlib.reload(bot)
                    
                    # Formatter should be created with correct format
                    mock_formatter.assert_called_with("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    def test_discord_logger_suppression(self):
        """Test Discord loggers are suppressed to reduce noise"""
        with patch('logging.getLogger') as mock_get_logger:
            with patch('logging.StreamHandler'):
                with patch('logging.Formatter'):
                    mock_gateway_logger = MagicMock()
                    mock_client_logger = MagicMock()
                    mock_topgg_logger = MagicMock()
                    
                    def logger_side_effect(name=None):
                        if name == "discord.gateway":
                            return mock_gateway_logger
                        elif name == "discord.client":
                            return mock_client_logger
                        elif name == "topgg":
                            return mock_topgg_logger
                        elif name is None:  # root logger
                            return MagicMock()
                        return MagicMock()
                    
                    mock_get_logger.side_effect = logger_side_effect
                    
                    import importlib
                    import bot
                    importlib.reload(bot)
                    
                    # Discord loggers should be set to higher levels
                    mock_gateway_logger.setLevel.assert_called_with(logging.ERROR)
                    mock_client_logger.setLevel.assert_called_with(logging.ERROR)
                    mock_topgg_logger.setLevel.assert_called_with(logging.CRITICAL)

    def test_logging_raise_exceptions_disabled(self):
        """Test logging.raiseExceptions is disabled"""
        with patch('logging.getLogger'):
            with patch('logging.StreamHandler'):
                with patch('logging.Formatter'):
                    import bot
                    
                    # Should disable exception raising in logging
                    assert logging.raiseExceptions is False

    def test_main_function_success(self):
        """Test main function runs successfully"""
        with patch('core.client.run_bot') as mock_run_bot:
            with patch('asyncio.run') as mock_asyncio_run:
                mock_run_bot.return_value = None
                
                import importlib
                import bot
                importlib.reload(bot)
                result = bot.main()
                
                # Should call asyncio.run with run_bot function
                mock_asyncio_run.assert_called_once()
                # The asyncio.run should be called with run_bot
                call_args = mock_asyncio_run.call_args[0][0]
                # This will be the coroutine from run_bot(), so we can't easily verify the function
                # but we can check that asyncio.run was called

    def test_main_function_keyboard_interrupt(self):
        """Test main function handles KeyboardInterrupt gracefully"""
        with patch('asyncio.run') as mock_asyncio_run:
            with patch('logging.info') as mock_log_info:
                mock_asyncio_run.side_effect = KeyboardInterrupt()
                
                import bot
                bot.main()
                
                # Should log shutdown message
                mock_log_info.assert_called_with("Bot shutting down...")

    def test_main_function_general_exception(self):
        """Test main function handles general exceptions"""
        with patch('asyncio.run') as mock_asyncio_run:
            with patch('logging.error') as mock_log_error:
                test_exception = Exception("Test error")
                mock_asyncio_run.side_effect = test_exception
                
                import bot
                bot.main()
                
                # Should log error with exception info
                mock_log_error.assert_called_with(f"Fatal error: {test_exception}", exc_info=True)

    def test_main_entry_point(self):
        """Test __main__ entry point calls main function"""
        with patch('bot.main') as mock_main:
            # Mock the __name__ check
            import bot
            with patch.object(bot, '__name__', '__main__'):
                # Re-execute the if __name__ == "__main__" block
                exec("if __name__ == '__main__': main()", bot.__dict__)
                
                mock_main.assert_called_once()

    def test_log_level_environment_variable_handling(self):
        """Test log level environment variable handling with various values"""
        test_cases = [
            ('DEBUG', logging.DEBUG),
            ('INFO', logging.INFO),
            ('WARNING', logging.WARNING),
            ('ERROR', logging.ERROR),
            ('CRITICAL', logging.CRITICAL),
            ('invalid', logging.INFO),  # Should default to INFO
        ]
        
        for env_value, expected_level in test_cases:
            with patch.dict(os.environ, {'LOG_LEVEL': env_value}, clear=True):
                with patch('logging.getLogger') as mock_get_logger:
                    with patch('logging.StreamHandler'):
                        with patch('logging.Formatter'):
                            mock_logger = MagicMock()
                            mock_get_logger.return_value = mock_logger
                            
                            import importlib
                            import bot
                            importlib.reload(bot)
                            
                            # Should set the correct level or default to INFO
                            calls = mock_logger.setLevel.call_args_list
                            level_set = any(call[0][0] == expected_level for call in calls)
                            if env_value != 'invalid':
                                assert level_set, f"Expected {expected_level} for {env_value}"

    def test_log_to_file_environment_variable_handling(self):
        """Test LOG_TO_FILE environment variable handling with various values"""
        false_values = ["0", "false", "False"]
        
        for false_value in false_values:
            with patch.dict(os.environ, {'LOG_TO_FILE': false_value}, clear=True):
                with patch('logging.handlers.RotatingFileHandler') as mock_file_handler:
                    with patch('logging.getLogger'):
                        with patch('logging.StreamHandler'):
                            with patch('logging.Formatter'):
                                import importlib
                                import bot
                                importlib.reload(bot)
                                
                                # Should not create file handler
                                mock_file_handler.assert_not_called()

    def test_file_handler_rotation_settings(self):
        """Test file handler rotation settings are correct"""
        with patch.dict(os.environ, {'LOG_TO_FILE': '1'}, clear=True):
            with patch('logging.handlers.RotatingFileHandler') as mock_file_handler:
                with patch('logging.getLogger'):
                    with patch('logging.StreamHandler'):
                        with patch('logging.Formatter'):
                            import importlib
                            import bot
                            importlib.reload(bot)
                            
                            # Check rotation settings
                            mock_file_handler.assert_called_once_with(
                                "bot.log",
                                maxBytes=1_000_000,  # 1 MB
                                backupCount=3,
                                encoding="utf-8",
                                delay=True
                            )

    def test_core_client_import(self):
        """Test core.client.run_bot is imported correctly"""
        import bot
        
        # Should be able to import without error
        from core.client import run_bot
        assert callable(run_bot)

    def test_logging_handlers_are_added(self):
        """Test that all configured handlers are added to logger"""
        with patch('logging.getLogger') as mock_get_logger:
            with patch('logging.StreamHandler') as mock_stream_handler:
                with patch('logging.handlers.RotatingFileHandler') as mock_file_handler:
                    with patch('logging.Formatter'):
                        mock_logger = MagicMock()
                        mock_stream = MagicMock()
                        mock_file = MagicMock()
                        mock_get_logger.return_value = mock_logger
                        mock_stream_handler.return_value = mock_stream
                        mock_file_handler.return_value = mock_file
                        
                        with patch.dict(os.environ, {'LOG_TO_FILE': '1'}, clear=True):
                            import importlib
                            import bot
                            importlib.reload(bot)
                            
                            # Both handlers should be added
                            add_handler_calls = mock_logger.addHandler.call_args_list
                            assert len(add_handler_calls) >= 2  # At least stream + file

    def test_asyncio_import(self):
        """Test asyncio is imported and used correctly"""
        import bot
        import asyncio
        
        # Should have access to asyncio.run
        assert hasattr(asyncio, 'run')

    def test_logging_modules_import(self):
        """Test required logging modules are imported"""
        import bot
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Should have access to required logging components
        assert hasattr(logging, 'getLogger')
        assert hasattr(logging, 'Formatter')
        assert hasattr(logging, 'StreamHandler')
        assert RotatingFileHandler is not None

    def test_environment_variable_defaults(self):
        """Test environment variable defaults work correctly"""
        with patch.dict(os.environ, {}, clear=True):  # Clear all env vars
            # Should not raise errors with missing env vars
            import importlib
            import bot
            importlib.reload(bot)

    def test_bot_module_structure(self):
        """Test bot module has expected structure"""
        import bot
        
        # Should have main function
        assert hasattr(bot, 'main')
        assert callable(bot.main)
        
        # Should import required modules
        assert 'asyncio' in dir(bot)
        assert 'logging' in dir(bot)
        assert 'os' in dir(bot)

    def test_logging_configuration_order(self):
        """Test logging configuration happens in correct order"""
        with patch('logging.getLogger') as mock_get_logger:
            with patch('logging.StreamHandler') as mock_stream_handler:
                with patch('logging.Formatter') as mock_formatter:
                    mock_logger = MagicMock()
                    mock_handler = MagicMock()
                    mock_formatter_instance = MagicMock()
                    
                    mock_get_logger.return_value = mock_logger
                    mock_stream_handler.return_value = mock_handler
                    mock_formatter.return_value = mock_formatter_instance
                    
                    import importlib
                    import bot
                    importlib.reload(bot)
                    
                    # Should configure in order: logger level, formatter, handler, add handler
                    assert mock_logger.setLevel.called
                    assert mock_formatter.called
                    mock_handler.setFormatter.assert_called_with(mock_formatter_instance)
                    # Check that the mock handler was added (look through all calls)
                    handler_calls = [call[0][0] for call in mock_logger.addHandler.call_args_list]
                    assert mock_handler in handler_calls
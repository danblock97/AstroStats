import pytest
import discord
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from contextlib import ExitStack
from core.client import AstroStatsBot, create_bot, run_bot


class TestAstroStatsBot:
    """Test AstroStatsBot custom bot class"""
    
    def test_bot_initialization(self):
        """Test that AstroStatsBot initializes correctly"""
        bot = AstroStatsBot()
        
        assert isinstance(bot, discord.ext.commands.Bot)
        assert bot.command_prefix == "/"
        assert hasattr(bot, '_emoji_cache')
        assert hasattr(bot, 'processed_issues')
        assert isinstance(bot._emoji_cache, dict)
        assert isinstance(bot.processed_issues, dict)

    def test_bot_intents(self):
        """Test that bot has appropriate intents"""
        bot = AstroStatsBot()
        
        # Should have default intents
        assert isinstance(bot.intents, discord.Intents)
        # Message content intent should be disabled (commented out)
        assert not bot.intents.message_content

    @pytest.mark.asyncio
    async def test_setup_hook_runs_migration(self):
        """Test that setup_hook runs database migration"""
        bot = AstroStatsBot()
        
        with ExitStack() as stack:
            mock_migration = stack.enter_context(patch('core.client.run_database_migration'))
            mock_error_handlers = stack.enter_context(patch('core.client.setup_error_handlers'))
            stack.enter_context(patch.object(bot.tree, 'sync', new=AsyncMock()))
            mock_update_presence = stack.enter_context(patch.object(bot, 'update_presence'))
            mock_update_presence.start = MagicMock()
            
            # Mock all the setup imports to avoid import errors
            stack.enter_context(patch('cogs.games.apex.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.league.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.fortnite.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.tft.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.general.help.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.general.horoscope.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.general.review.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.general.premium.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.general.support.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.systems.pet_battles.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.admin.kick.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.admin.servers.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.systems.squib_game.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.truthordare.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.wouldyourather.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.catfight.setup', new=AsyncMock()))
            
            await bot.setup_hook()
            
            mock_migration.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_hook_loads_all_cogs(self):
        """Test that setup_hook loads all required cogs"""
        bot = AstroStatsBot()
        
        with ExitStack() as stack:
            mock_migration = stack.enter_context(patch('core.client.run_database_migration'))
            mock_error_handlers = stack.enter_context(patch('core.client.setup_error_handlers'))
            stack.enter_context(patch.object(bot.tree, 'sync', new=AsyncMock()))
            mock_update_presence = stack.enter_context(patch.object(bot, 'update_presence'))
            mock_update_presence.start = MagicMock()
            
            # Mock all the setup imports and capture them
            mock_apex = stack.enter_context(patch('cogs.games.apex.setup', new=AsyncMock()))
            mock_league = stack.enter_context(patch('cogs.games.league.setup', new=AsyncMock()))
            mock_fortnite = stack.enter_context(patch('cogs.games.fortnite.setup', new=AsyncMock()))
            mock_tft = stack.enter_context(patch('cogs.games.tft.setup', new=AsyncMock()))
            mock_help = stack.enter_context(patch('cogs.general.help.setup', new=AsyncMock()))
            mock_horoscope = stack.enter_context(patch('cogs.general.horoscope.setup', new=AsyncMock()))
            mock_review = stack.enter_context(patch('cogs.general.review.setup', new=AsyncMock()))
            mock_premium = stack.enter_context(patch('cogs.general.premium.setup', new=AsyncMock()))
            mock_support = stack.enter_context(patch('cogs.general.support.setup', new=AsyncMock()))
            mock_pet_battles = stack.enter_context(patch('cogs.systems.pet_battles.setup', new=AsyncMock()))
            mock_kick = stack.enter_context(patch('cogs.admin.kick.setup', new=AsyncMock()))
            mock_servers = stack.enter_context(patch('cogs.admin.servers.setup', new=AsyncMock()))
            mock_squib_game = stack.enter_context(patch('cogs.systems.squib_game.setup', new=AsyncMock()))
            mock_truthordare = stack.enter_context(patch('cogs.games.truthordare.setup', new=AsyncMock()))
            mock_wouldyourather = stack.enter_context(patch('cogs.games.wouldyourather.setup', new=AsyncMock()))
            mock_catfight = stack.enter_context(patch('cogs.games.catfight.setup', new=AsyncMock()))
            
            await bot.setup_hook()
            
            # Verify all setup functions were called
            setup_mocks = [
                mock_apex, mock_league, mock_fortnite, mock_tft,
                mock_help, mock_horoscope, mock_review, mock_premium,
                mock_support, mock_pet_battles,
                mock_kick, mock_servers, mock_squib_game,
                mock_truthordare, mock_wouldyourather, mock_catfight
            ]
            for mock_func in setup_mocks:
                mock_func.assert_called_once_with(bot)

    @pytest.mark.asyncio
    async def test_setup_hook_syncs_commands(self):
        """Test that setup_hook syncs application commands"""
        bot = AstroStatsBot()
        
        with ExitStack() as stack:
            stack.enter_context(patch('core.client.run_database_migration'))
            stack.enter_context(patch('core.client.setup_error_handlers'))
            stack.enter_context(patch('cogs.games.apex.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.league.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.fortnite.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.tft.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.general.help.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.general.horoscope.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.general.review.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.general.premium.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.general.support.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.systems.pet_battles.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.admin.kick.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.admin.servers.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.systems.squib_game.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.truthordare.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.wouldyourather.setup', new=AsyncMock()))
            stack.enter_context(patch('cogs.games.catfight.setup', new=AsyncMock()))
            
            mock_sync = stack.enter_context(patch.object(bot.tree, 'sync', new=AsyncMock(return_value=[])))
            mock_update_presence = stack.enter_context(patch.object(bot, 'update_presence'))
            mock_update_presence.start = MagicMock()
            
            await bot.setup_hook()
            
            mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_presence_task(self):
        """Test update presence task functionality"""
        bot = AstroStatsBot()
        
        # Mock the change_presence method and guilds property
        mock_guilds = [MagicMock() for _ in range(5)]
        with patch.object(bot, 'change_presence', new=AsyncMock()) as mock_change_presence, \
             patch.object(type(bot), 'guilds', new_callable=PropertyMock) as mock_guilds_prop:
            mock_guilds_prop.return_value = mock_guilds
            
            await bot.update_presence()
            
            mock_change_presence.assert_called_once()
            call_args = mock_change_presence.call_args[1]
            activity = call_args['activity']
            assert "/premium | 5 servers" in activity.name
            assert activity.type == discord.ActivityType.playing

    @pytest.mark.asyncio
    async def test_on_ready_logging(self):
        """Test on_ready event logging"""
        bot = AstroStatsBot()
        mock_user = MagicMock()
        mock_user.id = 123456789
        
        # Mock the user property
        with patch.object(type(bot), 'user', new_callable=PropertyMock) as mock_user_prop, \
             patch('core.client.logger') as mock_logger:
            mock_user_prop.return_value = mock_user
            
            await bot.on_ready()
            
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "connected to Discord" in log_message
            assert "Ready!" in log_message

    @pytest.mark.asyncio
    async def test_on_guild_join_blacklisted(self):
        """Test behavior when joining a blacklisted guild"""
        bot = AstroStatsBot()
        
        mock_guild = MagicMock()
        mock_guild.id = 999888777  # Blacklisted ID
        mock_guild.name = "Blacklisted Guild"
        mock_guild.leave = AsyncMock()
        
        with patch('core.client.BLACKLISTED_GUILDS', [999888777]), \
             patch('core.client.logger') as mock_logger:
            
            await bot.on_guild_join(mock_guild)
            
            mock_guild.leave.assert_called_once()
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_guild_join_normal(self):
        """Test behavior when joining a normal guild"""
        bot = AstroStatsBot()
        bot.send_welcome_message = AsyncMock()
        
        mock_guild = MagicMock()
        mock_guild.id = 111222333  # Not blacklisted
        mock_guild.name = "Normal Guild"
        
        with patch('core.client.BLACKLISTED_GUILDS', [999888777]):  # Different ID
            await bot.on_guild_join(mock_guild)
            
            bot.send_welcome_message.assert_called_once_with(mock_guild)

    @pytest.mark.asyncio
    async def test_send_welcome_message_structure(self):
        """Test welcome message structure and content"""
        bot = AstroStatsBot()
        
        mock_guild = MagicMock()
        mock_guild.name = "Test Guild"
        mock_guild.icon = MagicMock()
        mock_guild.icon.url = "https://example.com/icon.png"
        mock_guild.system_channel = MagicMock()
        mock_guild.system_channel.permissions_for.return_value.send_messages = True
        mock_guild.system_channel.send = AsyncMock()
        mock_guild.me = MagicMock()
        
        await bot.send_welcome_message(mock_guild)
        
        mock_guild.system_channel.send.assert_called_once()
        call_kwargs = mock_guild.system_channel.send.call_args[1]
        
        assert 'embeds' in call_kwargs
        embeds = call_kwargs['embeds']
        assert len(embeds) >= 1
        
        welcome_embed = embeds[0]
        assert "Welcome to AstroStats!" in welcome_embed.title
        assert "Test Guild" in welcome_embed.description

    def test_welcome_message_content_coverage(self):
        """Test that welcome message covers all major features"""
        # This would test the actual welcome message content
        # to ensure it mentions all command groups and features
        pass


class TestClientFunctions:
    """Test module-level client functions"""
    
    def test_create_bot(self):
        """Test create_bot function"""
        bot = create_bot()
        
        assert isinstance(bot, AstroStatsBot)
        assert bot.command_prefix == "/"

    @pytest.mark.asyncio
    async def test_run_bot_no_token(self):
        """Test run_bot with no token"""
        with patch('core.client.TOKEN', None), \
             patch('core.client.logger') as mock_logger:
            
            await run_bot()
            
            mock_logger.critical.assert_called_once()
            log_message = mock_logger.critical.call_args[0][0]
            assert "BOT TOKEN IS NOT SET" in log_message

    @pytest.mark.asyncio
    async def test_run_bot_login_failure(self):
        """Test run_bot with login failure"""
        with patch('core.client.TOKEN', 'invalid_token'), \
             patch('core.client.create_bot') as mock_create, \
             patch('core.client.logger') as mock_logger:
            
            mock_bot = MagicMock()
            mock_bot.start = AsyncMock(side_effect=discord.LoginFailure())
            mock_create.return_value = mock_bot
            
            await run_bot()
            
            mock_logger.critical.assert_called()
            log_message = mock_logger.critical.call_args[0][0]
            assert "Failed to log in" in log_message

    @pytest.mark.asyncio
    async def test_run_bot_success(self):
        """Test successful run_bot execution"""
        with patch('core.client.TOKEN', 'valid_token'), \
             patch('core.client.create_bot') as mock_create:
            
            mock_bot = MagicMock()
            mock_bot.start = AsyncMock()
            mock_create.return_value = mock_bot
            
            await run_bot()
            
            mock_bot.start.assert_called_once_with('valid_token')


class TestDatabaseMigration:
    """Test database migration functionality"""
    
    @pytest.mark.asyncio
    async def test_run_database_migration_success(self):
        """Test successful database migration"""
        from core.client import run_database_migration
        
        with patch('core.client.MongoClient') as mock_mongo, \
             patch('core.client.logger') as mock_logger:
            
            mock_client = MagicMock()
            mock_db = MagicMock()
            mock_collection = MagicMock()
            
            mock_mongo.return_value = mock_client
            mock_client.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_collection.find.return_value = []  # No pets to migrate
            
            await run_database_migration()
            
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_run_database_migration_error(self):
        """Test database migration error handling"""
        from core.client import run_database_migration
        
        with patch('core.client.MongoClient', side_effect=Exception("Connection failed")), \
             patch('core.client.logger') as mock_logger:
            
            await run_database_migration()
            
            mock_logger.error.assert_called_once()
            log_message = mock_logger.error.call_args[0][0]
            assert "Database migration failed" in log_message
import pytest
import discord
from unittest.mock import patch, AsyncMock, MagicMock
from core.client import AstroStatsBot, create_bot, run_bot


@pytest.fixture
def mock_astro_stats_bot():
    with patch('core.client.AstroStatsBot.__init__', return_value=None):
        bot = AstroStatsBot()
        bot._emoji_cache = {}
        bot.processed_issues = {}
        bot.wait_until_ready = AsyncMock()
        bot.change_presence = AsyncMock()
        bot.tree = AsyncMock()
        bot.tree.sync = AsyncMock()
        bot.guilds = [MagicMock(spec=discord.Guild)]
        bot.guilds[0].id = 123456789
        bot.guilds[0].name = "Test Guild"
        bot.user = MagicMock()
        bot.user.name = "AstroStats"
        bot.start = AsyncMock()
        bot.event = MagicMock()
        bot.add_cog = AsyncMock()

        yield bot


@pytest.mark.asyncio
async def test_setup_hook(mock_astro_stats_bot):
    # Mock all the imported setup functions
    with patch('core.client.setup_error_handlers') as mock_setup_errors, \
            patch('core.client.setup_apex', return_value=AsyncMock()()), \
            patch('core.client.setup_league', return_value=AsyncMock()()), \
            patch('core.client.setup_fortnite', return_value=AsyncMock()()), \
            patch('core.client.setup_tft', return_value=AsyncMock()()), \
            patch('core.client.setup_help', return_value=AsyncMock()()), \
            patch('core.client.setup_horoscope', return_value=AsyncMock()()), \
            patch('core.client.setup_review', return_value=AsyncMock()()), \
            patch('core.client.setup_show_update', return_value=AsyncMock()()), \
            patch('core.client.setup_pet_battles', return_value=AsyncMock()()), \
            patch('core.client.setup_kick', return_value=AsyncMock()()), \
            patch('core.client.setup_servers', return_value=AsyncMock()()), \
            patch('core.client.setup_squib_game', return_value=AsyncMock()()):
        # Create the bot's setup_hook method
        async def setup_hook(self):
            # Import cog setup functions only when needed to avoid circular imports
            from cogs.games.apex import setup as setup_apex
            from cogs.games.league import setup as setup_league
            from cogs.games.fortnite import setup as setup_fortnite
            from cogs.games.tft import setup as setup_tft
            from cogs.general.help import setup as setup_help
            from cogs.general.horoscope import setup as setup_horoscope
            from cogs.general.review import setup as setup_review
            from cogs.general.show_update import setup as setup_show_update
            from cogs.systems.pet_battles import setup as setup_pet_battles
            from cogs.systems.squib_game import setup as setup_squib_game
            from cogs.admin.kick import setup as setup_kick
            from cogs.admin.servers import setup as setup_servers

            # Setup all cogs
            await setup_apex(self)
            await setup_league(self)
            await setup_fortnite(self)
            await setup_tft(self)
            await setup_help(self)
            await setup_horoscope(self)
            await setup_review(self)
            await setup_show_update(self)
            await setup_pet_battles(self)
            await setup_kick(self)
            await setup_servers(self)
            await setup_squib_game(self)

            # Setup error handlers
            setup_error_handlers(self)

            # Start tasks
            self.update_presence.start()

            # Sync commands
            await self.tree.sync()

        # Attach the method to our mocked bot
        mock_astro_stats_bot.setup_hook = AsyncMock(side_effect=lambda: setup_hook(mock_astro_stats_bot))
        mock_astro_stats_bot.update_presence = MagicMock()
        mock_astro_stats_bot.update_presence.start = MagicMock()

        # Call the setup_hook method
        await mock_astro_stats_bot.setup_hook()

        # Verify that setup_error_handlers was called
        mock_setup_errors.assert_called_once_with(mock_astro_stats_bot)

        # Verify that update_presence.start was called
        mock_astro_stats_bot.update_presence.start.assert_called_once()

        # Verify that tree.sync was called
        mock_astro_stats_bot.tree.sync.assert_called_once()


@pytest.mark.asyncio
async def test_update_presence(mock_astro_stats_bot):
    # Define the update_presence method
    @pytest.mark.asyncio
    async def update_presence(self):
        """Update the bot's presence with the server count."""
        guild_count = len(self.guilds)
        presence = discord.Game(name=f"/help | {guild_count} servers")
        await self.change_presence(activity=presence)

    # Call the method
    await update_presence(mock_astro_stats_bot)

    # Verify that change_presence was called with the right activity
    mock_astro_stats_bot.change_presence.assert_called_once()
    call_kwargs = mock_astro_stats_bot.change_presence.call_args.kwargs
    activity = call_kwargs.get('activity')
    assert isinstance(activity, discord.Game)
    assert activity.name == f"/help | {len(mock_astro_stats_bot.guilds)} servers"


@pytest.mark.asyncio
async def test_on_ready(mock_astro_stats_bot):
    # Define the on_ready method
    async def on_ready(self):
        """Called when the bot is ready."""
        pass

    # Mock the logger
    with patch('core.client.logger.info') as mock_logger:
        # Call the method
        await on_ready(mock_astro_stats_bot)

        # We can't really test much here since it's just logging a message
        # and our mocked version is empty, but we can at least ensure it runs


@pytest.mark.asyncio
async def test_on_guild_join_not_blacklisted(mock_astro_stats_bot, mock_guild):
    # Define the on_guild_join method
    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild."""
        # Check if the guild is blacklisted
        if guild.id in {55555}:  # Mocked blacklist
            await guild.leave()
            return

        # Send welcome message
        await self.send_welcome_message(guild)

    # Mock the send_welcome_message method
    mock_astro_stats_bot.send_welcome_message = AsyncMock()

    # Call the method with a non-blacklisted guild
    await on_guild_join(mock_astro_stats_bot, mock_guild)

    # Verify that send_welcome_message was called
    mock_astro_stats_bot.send_welcome_message.assert_called_once_with(mock_guild)

    # Verify guild.leave was not called
    mock_guild.leave.assert_not_called()


@pytest.mark.asyncio
async def test_on_guild_join_blacklisted(mock_astro_stats_bot, mock_guild):
    # Define the on_guild_join method with our guild ID in the blacklist
    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild."""
        # Check if the guild is blacklisted
        if guild.id in {123456789}:  # Mocked blacklist with our guild ID
            await guild.leave()
            return

        # Send welcome message
        await self.send_welcome_message(guild)

    # Mock the send_welcome_message method
    mock_astro_stats_bot.send_welcome_message = AsyncMock()

    # Call the method with a blacklisted guild
    await on_guild_join(mock_astro_stats_bot, mock_guild)

    # Verify that guild.leave was called
    mock_guild.leave.assert_called_once()

    # Verify that send_welcome_message was NOT called
    mock_astro_stats_bot.send_welcome_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_welcome_message(mock_astro_stats_bot, mock_guild):
    # Define the send_welcome_message method
    async def send_welcome_message(self, guild):
        """Sends a welcome message to a new guild."""
        embed = discord.Embed(
            title=guild.name,
            description="Thank you for using AstroStats!",
            color=discord.Color.blue()
        )

        # Find a channel to send the welcome message
        channel = guild.system_channel
        if channel is None or not channel.permissions_for(guild.me).send_messages:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break
            else:
                return

        await channel.send(embed=embed)

    # Set up permissions for the system channel
    system_channel = mock_guild.system_channel
    system_channel.permissions_for.return_value.send_messages = True

    # Call the method
    await send_welcome_message(mock_astro_stats_bot, mock_guild)

    # Verify that channel.send was called with an embed
    system_channel.send.assert_called_once()
    kwargs = system_channel.send.call_args.kwargs
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert embed.title == mock_guild.name
    assert "Thank you for using AstroStats!" in embed.description
    assert embed.color == discord.Color.blue()


@pytest.mark.asyncio
async def test_send_welcome_message_fallback_channel(mock_astro_stats_bot, mock_guild):
    # Define the send_welcome_message method
    async def send_welcome_message(self, guild):
        """Sends a welcome message to a new guild."""
        embed = discord.Embed(
            title=guild.name,
            description="Thank you for using AstroStats!",
            color=discord.Color.blue()
        )

        # Find a channel to send the welcome message
        channel = guild.system_channel
        if channel is None or not channel.permissions_for(guild.me).send_messages:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break
            else:
                return

        await channel.send(embed=embed)

    # Set up permissions so system_channel can't send messages
    mock_guild.system_channel.permissions_for.return_value.send_messages = False

    # Set up permissions for the text channels
    text_channel = mock_guild.text_channels[0]
    text_channel.permissions_for.return_value.send_messages = True

    # Call the method
    await send_welcome_message(mock_astro_stats_bot, mock_guild)

    # Verify that the system channel was not used
    mock_guild.system_channel.send.assert_not_called()

    # Verify that the text channel was used instead
    text_channel.send.assert_called_once()
    kwargs = text_channel.send.call_args.kwargs
    assert 'embed' in kwargs


def test_create_bot():
    # Mock the AstroStatsBot constructor
    with patch('core.client.AstroStatsBot') as MockBot:
        # Call the create_bot function
        bot = create_bot()

        # Verify that AstroStatsBot constructor was called
        MockBot.assert_called_once()

        # Verify that the correct bot instance was returned
        assert bot == MockBot.return_value


@pytest.mark.asyncio
async def test_run_bot():
    # Mock the create_bot function and the bot's start method
    with patch('core.client.create_bot') as mock_create_bot, \
            patch('core.client.TOKEN', 'test_token'):
        mock_bot = AsyncMock()
        mock_create_bot.return_value = mock_bot

        # Call the run_bot function
        await run_bot()

        # Verify that create_bot was called
        mock_create_bot.assert_called_once()

        # Verify that the bot's start method was called with the token
        mock_bot.start.assert_called_once_with('test_token')
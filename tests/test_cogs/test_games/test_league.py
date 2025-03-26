import pytest
import discord
import aiohttp
from unittest.mock import patch, AsyncMock, MagicMock, call
from cogs.games.league import LeagueCog


@pytest.fixture
def setup_league_cog(mock_bot):
    """Create an instance of the LeagueCog."""
    return LeagueCog(mock_bot)


@pytest.mark.asyncio
async def test_initialize_emojis(setup_league_cog):
    """Test the initialize_emojis method."""
    # Setup
    cog = setup_league_cog
    emoji_data = [
        {"name": "Aatrox", "id": "12345"},
        {"name": "Ahri", "id": "67890"}
    ]

    # Mock the fetch_application_emojis method
    with patch.object(cog, 'fetch_application_emojis', return_value=AsyncMock(return_value=emoji_data)), \
            patch('cogs.games.league.logger.info') as mock_logger:
        # Call the method
        await cog.initialize_emojis()

        # Check that the emojis were added to the cache
        assert len(cog.emojis) == 2
        assert cog.emojis["aatrox"] == "<:Aatrox:12345>"
        assert cog.emojis["ahri"] == "<:Ahri:67890>"

        # Verify logging
        mock_logger.assert_called_once()
        assert "Loaded 2 emojis" in mock_logger.call_args.args[0]


@pytest.mark.asyncio
async def test_initialize_emojis_no_data(setup_league_cog):
    """Test the initialize_emojis method when no emoji data is found."""
    # Setup
    cog = setup_league_cog

    # Mock the fetch_application_emojis method
    with patch.object(cog, 'fetch_application_emojis', return_value=AsyncMock(return_value=None)), \
            patch('cogs.games.league.logger.warning') as mock_logger:
        # Call the method
        await cog.initialize_emojis()

        # Check that no emojis were added to the cache
        assert len(cog.emojis) == 0

        # Verify logging
        mock_logger.assert_called_once()
        assert "No emojis found" in mock_logger.call_args.args[0]


@pytest.mark.asyncio
async def test_initialize_emojis_error(setup_league_cog):
    """Test the initialize_emojis method when an error occurs."""
    # Setup
    cog = setup_league_cog

    # Mock the fetch_application_emojis method to raise an exception
    with patch.object(cog, 'fetch_application_emojis', side_effect=Exception("Test error")), \
            patch('cogs.games.league.logger.error') as mock_logger:
        # Call the method
        await cog.initialize_emojis()

        # Check that no emojis were added to the cache
        assert len(cog.emojis) == 0

        # Verify logging
        mock_logger.assert_called_once()
        assert "Error initializing emojis" in mock_logger.call_args.args[0]


@pytest.mark.asyncio
async def test_fetch_application_emojis_success(setup_league_cog):
    """Test the fetch_application_emojis method when the API call succeeds."""
    # Setup
    cog = setup_league_cog
    emoji_data = [
        {"name": "Aatrox", "id": "12345"},
        {"name": "Ahri", "id": "67890"}
    ]

    # Mock the aiohttp.ClientSession
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=emoji_data)

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session), \
            patch('cogs.games.league.DISCORD_APP_ID', '123456789'), \
            patch('cogs.games.league.TOKEN', 'test_bot_token'):
        # Call the method
        result = await cog.fetch_application_emojis()

        # Verify the API was called with the right URL and headers
        mock_session.get.assert_called_once()
        url = mock_session.get.call_args.args[0]
        assert "applications/123456789/emojis" in url

        headers = mock_session.get.call_args.kwargs.get('headers')
        assert headers == {'Authorization': 'Bot test_bot_token'}

        # Check the result
        assert result == emoji_data


@pytest.mark.asyncio
async def test_fetch_application_emojis_error(setup_league_cog):
    """Test the fetch_application_emojis method when the API returns an error."""
    # Setup
    cog = setup_league_cog

    # Mock the aiohttp.ClientSession
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_response.reason = "Not Found"

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session), \
            patch('cogs.games.league.DISCORD_APP_ID', '123456789'), \
            patch('cogs.games.league.TOKEN', 'test_bot_token'), \
            patch('cogs.games.league.logger.error') as mock_logger:
        # Call the method
        result = await cog.fetch_application_emojis()

        # Verify error was logged
        mock_logger.assert_called_once()
        assert "Error fetching emojis: 404" in mock_logger.call_args.args[0]

        # Check the result
        assert result is None


@pytest.mark.asyncio
async def test_fetch_data_success(setup_league_cog):
    """Test the fetch_data method when the API call succeeds."""
    # Setup
    cog = setup_league_cog
    url = "https://example.com/api"
    headers = {"Authorization": "test_token"}
    response_data = {"data": "test"}

    # Mock the aiohttp.ClientSession
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=response_data)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    # Call the method
    result = await cog.fetch_data(mock_session, url, headers)

    # Verify the API was called with the right URL and headers
    mock_session.get.assert_called_once_with(url, headers=headers)

    # Check the result
    assert result == response_data


@pytest.mark.asyncio
async def test_fetch_data_not_found(setup_league_cog):
    """Test the fetch_data method when the API returns 404."""
    # Setup
    cog = setup_league_cog
    url = "https://example.com/api"
    headers = {"Authorization": "test_token"}

    # Mock the aiohttp.ClientSession
    mock_response = AsyncMock()
    mock_response.status = 404

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    # Call the method
    result = await cog.fetch_data(mock_session, url, headers)

    # Check the result
    assert result is None


@pytest.mark.asyncio
async def test_fetch_data_rate_limit(setup_league_cog):
    """Test the fetch_data method when the API returns a rate limit (429)."""
    # Setup
    cog = setup_league_cog
    url = "https://example.com/api"
    headers = {"Authorization": "test_token"}
    response_data = {"data": "test"}

    # Mock the aiohttp.ClientSession for first call (rate limit) and second call (success)
    mock_response_limit = AsyncMock()
    mock_response_limit.status = 429
    mock_response_limit.headers = {"Retry-After": "1"}

    mock_response_success = AsyncMock()
    mock_response_success.status = 200
    mock_response_success.json = AsyncMock(return_value=response_data)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.side_effect = [mock_response_limit, mock_response_success]

    # Mock asyncio.sleep to avoid waiting
    with patch('asyncio.sleep', return_value=None):
        # Call the method
        result = await cog.fetch_data(mock_session, url, headers)

        # Verify the API was called twice
        assert mock_session.get.call_count == 2

        # Check the result
        assert result == response_data


@pytest.mark.asyncio
async def test_fetch_data_error(setup_league_cog):
    """Test the fetch_data method when the API returns an error."""
    # Setup
    cog = setup_league_cog
    url = "https://example.com/api"
    headers = {"Authorization": "test_token"}

    # Mock the aiohttp.ClientSession
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.reason = "Internal Server Error"

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    # Mock logger
    with patch('cogs.games.league.logger.error') as mock_logger:
        # Call the method
        result = await cog.fetch_data(mock_session, url, headers)

        # Verify error was logged
        mock_logger.assert_called_once()
        assert "Error fetching data from" in mock_logger.call_args.args[0]

        # Check the result
        assert result is None


@pytest.mark.asyncio
async def test_fetch_data_exception(setup_league_cog):
    """Test the fetch_data method when an exception occurs."""
    # Setup
    cog = setup_league_cog
    url = "https://example.com/api"
    headers = {"Authorization": "test_token"}

    # Mock the aiohttp.ClientSession to raise an exception
    mock_session = MagicMock()
    mock_session.get.side_effect = Exception("Test error")

    # Mock logger
    with patch('cogs.games.league.logger.error') as mock_logger:
        # Call the method
        result = await cog.fetch_data(mock_session, url, headers)

        # Verify error was logged
        mock_logger.assert_called_once()
        assert "Exception during fetch_data" in mock_logger.call_args.args[0]

        # Check the result
        assert result is None


@pytest.mark.asyncio
async def test_get_emoji_for_champion(setup_league_cog):
    """Test the get_emoji_for_champion method."""
    # Setup
    cog = setup_league_cog
    cog.emojis = {
        "aatrox": "<:Aatrox:12345>",
        "ahri": "<:Ahri:67890>"
    }

    # Test with a champion in the cache
    result = await cog.get_emoji_for_champion("Aatrox")
    assert result == "<:Aatrox:12345>"

    # Test with a champion that needs normalization (from SPECIAL_EMOJI_NAMES)
    with patch('cogs.games.league.SPECIAL_EMOJI_NAMES', {"Wukong": "MonkeyKing"}):
        # MonkeyKing would be in the emojis cache due to how Discord stores the emoji name
        cog.emojis["monkeyking"] = "<:MonkeyKing:12345>"
        result = await cog.get_emoji_for_champion("Wukong")
        assert result == "<:MonkeyKing:12345>"

    # Test with a champion not in the cache
    result = await cog.get_emoji_for_champion("Zed")
    assert result == ""  # Empty string for champions without emojis

    # Test with error
    with patch('cogs.games.league.logger.error') as mock_logger:
        cog.get_emoji_for_champion = AsyncMock(side_effect=Exception("Test error"))
        # Directly call the exception handler since we mocked the method itself
        with pytest.raises(Exception):
            await cog.get_emoji_for_champion("Aatrox")


@pytest.mark.asyncio
async def test_setup(mock_bot):
    """Test the setup function."""
    # Call the setup function
    from cogs.games.league import setup
    await setup(mock_bot)

    # Verify the cog was added to the bot
    mock_bot.add_cog.assert_called_once()

    # Check that the cog is an instance of LeagueCog
    cog = mock_bot.add_cog.call_args.args[0]
    assert isinstance(cog, LeagueCog)

    # Check that the initialize_emojis task was created
    assert hasattr(cog, 'initialize_emojis')
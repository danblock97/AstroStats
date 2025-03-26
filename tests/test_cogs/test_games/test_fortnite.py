import pytest
import discord
import aiohttp
from unittest.mock import patch, AsyncMock, MagicMock
from cogs.games.fortnite import FortniteCog


@pytest.fixture
def setup_fortnite_cog(mock_bot):
    """Create an instance of the FortniteCog."""
    return FortniteCog(mock_bot)


@pytest.fixture
def mock_fortnite_stats_response():
    """Create a mock Fortnite stats response."""
    return {
        "data": {
            "account": {
                "name": "TestPlayer"
            },
            "battlePass": {
                "level": 85
            },
            "stats": {
                "all": {
                    "overall": {
                        "wins": 50,
                        "top5": 150,
                        "top12": 300,
                        "kills": 1000,
                        "deaths": 500,
                        "kd": 2.0,
                        "killsPerMin": 0.5,
                        "killsPerMatch": 2.5,
                        "playersOutlived": 5000,
                        "matches": 400,
                        "score": 50000,
                        "scorePerMin": 120,
                        "scorePerMatch": 125,
                        "minutesPlayed": 600
                    }
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_fetch_fortnite_stats_success(setup_fortnite_cog, mock_fortnite_stats_response):
    """Test fetching Fortnite stats when the API call succeeds."""
    # Setup
    cog = setup_fortnite_cog
    name = "TestPlayer"
    time_window = "season"

    # Mock the aiohttp.ClientSession
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_fortnite_stats_response)

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session), \
            patch('cogs.games.fortnite.FORTNITE_API_KEY', 'test_api_key'):
        # Call the method
        result = await cog.fetch_fortnite_stats(name, time_window)

        # Verify the API was called with the right URL and headers
        mock_session.get.assert_called_once()
        url = mock_session.get.call_args.args[0]
        assert time_window in url
        assert name in url

        headers = mock_session.get.call_args.kwargs.get('headers')
        assert headers == {"Authorization": "test_api_key"}

        # Check the result
        assert result == mock_fortnite_stats_response


@pytest.mark.asyncio
async def test_fetch_fortnite_stats_not_found(setup_fortnite_cog):
    """Test fetching Fortnite stats when the player is not found."""
    # Setup
    cog = setup_fortnite_cog
    name = "NonExistentPlayer"
    time_window = "season"

    # Mock the aiohttp.ClientSession
    mock_response = AsyncMock()
    mock_response.status = 404

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session), \
            patch('cogs.games.fortnite.FORTNITE_API_KEY', 'test_api_key'):
        # Call the method
        result = await cog.fetch_fortnite_stats(name, time_window)

        # Check the result
        assert result is None


@pytest.mark.asyncio
async def test_fetch_fortnite_stats_error(setup_fortnite_cog):
    """Test fetching Fortnite stats when the API returns an error."""
    # Setup
    cog = setup_fortnite_cog
    name = "TestPlayer"
    time_window = "season"

    # Mock the aiohttp.ClientSession
    mock_response = AsyncMock()
    mock_response.status = 500

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session), \
            patch('cogs.games.fortnite.FORTNITE_API_KEY', 'test_api_key'), \
            patch('cogs.games.fortnite.logger.error') as mock_logger:
        # Call the method
        result = await cog.fetch_fortnite_stats(name, time_window)

        # Verify error was logged
        mock_logger.assert_called_once()

        # Check the result
        assert result is None


@pytest.mark.asyncio
async def test_fetch_fortnite_stats_client_error(setup_fortnite_cog):
    """Test fetching Fortnite stats when a client error occurs."""
    # Setup
    cog = setup_fortnite_cog
    name = "TestPlayer"
    time_window = "season"

    # Mock the aiohttp.ClientSession to raise an exception
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get.side_effect = aiohttp.ClientError("Network error")

    with patch('aiohttp.ClientSession', return_value=mock_session), \
            patch('cogs.games.fortnite.FORTNITE_API_KEY', 'test_api_key'), \
            patch('cogs.games.fortnite.logger.error') as mock_logger:
        # Call the method
        result = await cog.fetch_fortnite_stats(name, time_window)

        # Verify error was logged
        mock_logger.assert_called_once()

        # Check the result
        assert result is None


@pytest.mark.asyncio
async def test_fortnite_command_success(setup_fortnite_cog, mock_interaction, mock_fortnite_stats_response):
    """Test the fortnite command when the API call succeeds."""
    # Setup
    cog = setup_fortnite_cog
    time = "Season"
    name = "TestPlayer"

    # Mock the fetch_fortnite_stats method
    with patch.object(cog, 'fetch_fortnite_stats', return_value=mock_fortnite_stats_response), \
            patch('cogs.games.fortnite.get_conditional_embed', return_value=None), \
            patch('cogs.games.fortnite.FORTNITE_TIME_MAPPING', {'Season': 'season'}):
        # Call the command
        await cog.fortnite(mock_interaction, time, name)

        # Verify interaction.response.defer was called
        mock_interaction.response.defer.assert_called_once()

        # Verify fetch_fortnite_stats was called with the right parameters
        cog.fetch_fortnite_stats.assert_called_once_with(name, 'season')

        # Verify followup.send was called with embeds
        mock_interaction.followup.send.assert_called_once()
        called_with_kwargs = mock_interaction.followup.send.call_args[1]
        assert 'embeds' in called_with_kwargs

        # Check the main embed's content
        embeds = called_with_kwargs['embeds']
        assert len(embeds) >= 1

        main_embed = embeds[0]
        assert "Fortnite - TestPlayer" in main_embed.title
        assert isinstance(main_embed, discord.Embed)


@pytest.mark.asyncio
async def test_fortnite_command_no_name(setup_fortnite_cog, mock_interaction):
    """Test the fortnite command when no name is provided."""
    # Setup
    cog = setup_fortnite_cog
    time = "Season"
    name = None

    # Mock the send_error_embed function
    with patch('cogs.games.fortnite.send_error_embed') as mock_error:
        # Call the command
        await cog.fortnite(mock_interaction, time, name)

        # Verify error handling
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Missing Username"


@pytest.mark.asyncio
async def test_fortnite_command_invalid_time(setup_fortnite_cog, mock_interaction):
    """Test the fortnite command with an invalid time window."""
    # Setup
    cog = setup_fortnite_cog
    time = "Invalid"
    name = "TestPlayer"

    # Mock the FORTNITE_TIME_MAPPING to not include the time
    with patch('cogs.games.fortnite.FORTNITE_TIME_MAPPING', {'Season': 'season'}), \
            patch('cogs.games.fortnite.send_error_embed') as mock_error:
        # Call the command
        await cog.fortnite(mock_interaction, time, name)

        # Verify error handling
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Invalid Time Window"


@pytest.mark.asyncio
async def test_fortnite_command_player_not_found(setup_fortnite_cog, mock_interaction):
    """Test the fortnite command when the player is not found."""
    # Setup
    cog = setup_fortnite_cog
    time = "Season"
    name = "NonExistentPlayer"

    # Mock the fetch_fortnite_stats method to return None
    with patch.object(cog, 'fetch_fortnite_stats', return_value=None), \
            patch('cogs.games.fortnite.FORTNITE_TIME_MAPPING', {'Season': 'season'}), \
            patch('cogs.games.fortnite.send_error_embed') as mock_error:
        # Call the command
        await cog.fortnite(mock_interaction, time, name)

        # Verify error handling
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Account Not Found"


@pytest.mark.asyncio
async def test_fortnite_command_api_error(setup_fortnite_cog, mock_interaction):
    """Test the fortnite command when the API returns an error."""
    # Setup
    cog = setup_fortnite_cog
    time = "Season"
    name = "TestPlayer"

    # Mock the fetch_fortnite_stats method to return data without 'data'
    with patch.object(cog, 'fetch_fortnite_stats', return_value={"error": "API error"}), \
            patch('cogs.games.fortnite.FORTNITE_TIME_MAPPING', {'Season': 'season'}), \
            patch('cogs.games.fortnite.send_error_embed') as mock_error:
        # Call the command
        await cog.fortnite(mock_interaction, time, name)

        # Verify error handling
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Account Not Found"


@pytest.mark.asyncio
async def test_fortnite_command_unexpected_error(setup_fortnite_cog, mock_interaction):
    """Test the fortnite command when an unexpected error occurs."""
    # Setup
    cog = setup_fortnite_cog
    time = "Season"
    name = "TestPlayer"

    # Mock the fetch_fortnite_stats method to raise an exception
    with patch.object(cog, 'fetch_fortnite_stats', side_effect=Exception("Unexpected error")), \
            patch('cogs.games.fortnite.FORTNITE_TIME_MAPPING', {'Season': 'season'}), \
            patch('cogs.games.fortnite.logger.error') as mock_logger, \
            patch('cogs.games.fortnite.send_error_embed') as mock_error:
        # Call the command
        await cog.fortnite(mock_interaction, time, name)

        # Verify error handling
        mock_logger.assert_called_once()
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Unexpected Error"


def test_build_embed(setup_fortnite_cog, mock_fortnite_stats_response):
    """Test the build_embed method."""
    # Setup
    cog = setup_fortnite_cog
    name = "TestPlayer"
    account = mock_fortnite_stats_response['data']['account']
    battle_pass = mock_fortnite_stats_response['data']['battlePass']
    stats = mock_fortnite_stats_response['data']

    # Since wins/matches are used for the calculated_win_rate parameter
    wins = stats['stats']['all']['overall']['wins']
    matches = stats['stats']['all']['overall']['matches']
    calculated_win_rate = wins / matches

    # Call the method
    embed = cog.build_embed(name, account, battle_pass, stats, calculated_win_rate)

    # Check the embed's properties
    assert isinstance(embed, discord.Embed)
    assert "Fortnite - TestPlayer" in embed.title
    assert embed.color.value == 0xdd4f7a

    # Check the account field
    account_field = None
    for field in embed.fields:
        if field.name == "Account":
            account_field = field
            break
    assert account_field is not None
    assert account['name'] in account_field.value
    assert str(battle_pass['level']) in account_field.value

    # Check the match placements field
    match_field = None
    for field in embed.fields:
        if field.name == "Match Placements":
            match_field = field
            break
    assert match_field is not None
    assert str(stats['stats']['all']['overall']['wins']) in match_field.value
    assert str(stats['stats']['all']['overall']['top5']) in match_field.value
    assert str(stats['stats']['all']['overall']['top12']) in match_field.value

    # Check the kill stats field
    kill_field = None
    for field in embed.fields:
        if field.name == "Kill Stats":
            kill_field = field
            break
    assert kill_field is not None
    assert str(stats['stats']['all']['overall']['kills']) in kill_field.value
    assert str(stats['stats']['all']['overall']['deaths']) in kill_field.value
    assert str(stats['stats']['all']['overall']['kd']) in kill_field.value

    # Check the match stats field
    match_stats_field = None
    for field in embed.fields:
        if field.name == "Match Stats":
            match_stats_field = field
            break
    assert match_stats_field is not None
    assert str(stats['stats']['all']['overall']['matches']) in match_stats_field.value
    assert f"{calculated_win_rate:.2%}" in match_stats_field.value

    # Check the support field
    support_field = None
    for field in embed.fields:
        if field.name == "Support Us ❤️":
            support_field = field
            break
    assert support_field is not None
    assert "buymeacoffee.com" in support_field.value


@pytest.mark.asyncio
async def test_setup(mock_bot):
    """Test the setup function."""
    # Call the setup function
    from cogs.games.fortnite import setup
    await setup(mock_bot)

    # Verify the cog was added to the bot
    mock_bot.add_cog.assert_called_once()

    # Check that the cog is an instance of FortniteCog
    cog = mock_bot.add_cog.call_args.args[0]
    assert isinstance(cog, FortniteCog)
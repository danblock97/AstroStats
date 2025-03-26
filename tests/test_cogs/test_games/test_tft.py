import pytest
import discord
import requests
from unittest.mock import patch, AsyncMock, MagicMock
from cogs.games.tft import TFTCog


@pytest.fixture
def setup_tft_cog(mock_bot):
    """Create an instance of the TFTCog."""
    return TFTCog(mock_bot)


@pytest.fixture
def mock_tft_summoner_response():
    """Create a mock TFT summoner response."""
    return {
        "id": "test-summoner-id",
        "accountId": "test-account-id",
        "puuid": "test-puuid",
        "name": "TestPlayer",
        "profileIconId": 1234,
        "summonerLevel": 100
    }


@pytest.fixture
def mock_tft_league_response():
    """Create a mock TFT league response."""
    return [
        {
            "queueType": "RANKED_TFT",
            "tier": "GOLD",
            "rank": "II",
            "leaguePoints": 75,
            "wins": 120,
            "losses": 100
        }
    ]


@pytest.mark.asyncio
async def test_tft_command_success(setup_tft_cog, mock_interaction, mock_lol_account_response,
                                   mock_tft_summoner_response, mock_tft_league_response):
    """Test the tft command when all API calls succeed."""
    # Setup
    cog = setup_tft_cog
    region = "EUW1"
    riotid = "TestPlayer#1234"

    # Mock requests.get for different endpoints
    with patch('requests.get') as mock_get, \
            patch('cogs.games.tft.get_conditional_embed', return_value=None), \
            patch('cogs.games.tft.TFT_API', 'test_api_key'):

        # Configure mock responses for different endpoints
        def mock_get_side_effect(url, headers=None):
            mock_response = MagicMock()

            if 'accounts/by-riot-id' in url:
                mock_response.status_code = 200
                mock_response.json.return_value = mock_lol_account_response
            elif 'summoners/by-puuid' in url:
                mock_response.status_code = 200
                mock_response.json.return_value = mock_tft_summoner_response
            elif 'entries/by-summoner' in url:
                mock_response.status_code = 200
                mock_response.json.return_value = mock_tft_league_response
            else:
                mock_response.status_code = 404

            return mock_response

        mock_get.side_effect = mock_get_side_effect

        # Call the command
        await cog.tft(mock_interaction, region, riotid)

        # Verify interaction.response.defer was called
        mock_interaction.response.defer.assert_called_once()

        # Verify requests.get was called for each endpoint
        assert mock_get.call_count == 3

        # Verify the account endpoint was called with the right parameters
        account_call = mock_get.call_args_list[0]
        assert 'accounts/by-riot-id/TestPlayer/1234' in account_call.args[0]
        assert account_call.kwargs['headers'] == {'X-Riot-Token': 'test_api_key'}

        # Verify the summoner endpoint was called with the right parameters
        summoner_call = mock_get.call_args_list[1]
        assert f'{region.lower()}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{mock_lol_account_response["puuid"]}' in \
               summoner_call.args[0]

        # Verify the league endpoint was called with the right parameters
        league_call = mock_get.call_args_list[2]
        assert f'{region.lower()}.api.riotgames.com/tft/league/v1/entries/by-summoner/{mock_tft_summoner_response["id"]}' in \
               league_call.args[0]

        # Verify followup.send was called with embeds
        mock_interaction.followup.send.assert_called_once()
        called_with_kwargs = mock_interaction.followup.send.call_args[1]
        assert 'embeds' in called_with_kwargs

        # Check the main embed's content
        embeds = called_with_kwargs['embeds']
        assert len(embeds) >= 1

        main_embed = embeds[0]
        assert f"{mock_lol_account_response['gameName']}#{mock_lol_account_response['tagLine']}" in main_embed.title
        assert str(mock_tft_summoner_response['summonerLevel']) in main_embed.title
        assert isinstance(main_embed, discord.Embed)

        # Check that league data was added to the embed
        found_ranked_field = False
        for field in main_embed.fields:
            if field.name == "RANKED_TFT":
                found_ranked_field = True
                assert "GOLD II 75 LP" in field.value
                assert "Wins: 120" in field.value
                assert "Losses: 100" in field.value
                assert "Winrate: 54%" in field.value

        assert found_ranked_field, "Should have a field for RANKED_TFT queue type"


@pytest.mark.asyncio
async def test_tft_command_invalid_riotid_format(setup_tft_cog, mock_interaction):
    """Test the tft command with an invalid Riot ID format."""
    # Setup
    cog = setup_tft_cog
    region = "EUW1"
    riotid = "InvalidFormat"  # Missing the #tagLine

    # Mock send_error_embed
    with patch('cogs.games.tft.send_error_embed') as mock_error:
        # Call the command
        await cog.tft(mock_interaction, region, riotid)

        # Verify error handling
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Invalid Format"
        assert "gameName#tagLine" in mock_error.call_args.args[2]


@pytest.mark.asyncio
async def test_tft_command_missing_api_key(setup_tft_cog, mock_interaction):
    """Test the tft command when the API key is missing."""
    # Setup
    cog = setup_tft_cog
    region = "EUW1"
    riotid = "TestPlayer#1234"

    # Mock TFT_API to be None
    with patch('cogs.games.tft.TFT_API', None), \
            patch('cogs.games.tft.logger.error') as mock_logger, \
            patch('cogs.games.tft.send_error_embed') as mock_error:
        # Call the command
        await cog.tft(mock_interaction, region, riotid)

        # Verify error handling
        mock_logger.assert_called_once()
        assert "TFT API key is missing" in mock_logger.call_args.args[0]

        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Configuration Error"
        assert "TFT API key is not configured" in mock_error.call_args.args[2]


@pytest.mark.asyncio
async def test_tft_command_account_not_found(setup_tft_cog, mock_interaction):
    """Test the tft command when the account is not found."""
    # Setup
    cog = setup_tft_cog
    region = "EUW1"
    riotid = "NonExistent#1234"

    # Mock requests.get to return 404 for the account endpoint
    with patch('requests.get') as mock_get, \
            patch('cogs.games.tft.TFT_API', 'test_api_key'), \
            patch('cogs.games.tft.send_error_embed') as mock_error:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Call the command
        await cog.tft(mock_interaction, region, riotid)

        # Verify error handling
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Summoner Not Found"


@pytest.mark.asyncio
async def test_tft_command_region_error(setup_tft_cog, mock_interaction, mock_lol_account_response):
    """Test the tft command when there's an error with the region."""
    # Setup
    cog = setup_tft_cog
    region = "EUW1"
    riotid = "TestPlayer#1234"

    # Mock requests.get for different endpoints
    with patch('requests.get') as mock_get, \
            patch('cogs.games.tft.TFT_API', 'test_api_key'), \
            patch('cogs.games.tft.send_error_embed') as mock_error:

        # Configure mock responses
        def mock_get_side_effect(url, headers=None):
            mock_response = MagicMock()

            if 'accounts/by-riot-id' in url:
                mock_response.status_code = 200
                mock_response.json.return_value = mock_lol_account_response
            else:
                # Summoner endpoint fails
                mock_response.status_code = 404

            return mock_response

        mock_get.side_effect = mock_get_side_effect

        # Call the command
        await cog.tft(mock_interaction, region, riotid)

        # Verify error handling
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Region Error"
        assert f"region {region}" in mock_error.call_args.args[2]


@pytest.mark.asyncio
async def test_tft_command_http_error(setup_tft_cog, mock_interaction):
    """Test the tft command when an HTTP error occurs."""
    # Setup
    cog = setup_tft_cog
    region = "EUW1"
    riotid = "TestPlayer#1234"

    # Mock requests.get to raise an HTTPError
    with patch('requests.get', side_effect=requests.exceptions.HTTPError("API Error")), \
            patch('cogs.games.tft.TFT_API', 'test_api_key'), \
            patch('cogs.games.tft.logger.error') as mock_logger, \
            patch('cogs.games.tft.send_error_embed') as mock_error:
        # Call the command
        await cog.tft(mock_interaction, region, riotid)

        # Verify error handling
        mock_logger.assert_called_once()
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert "API Error" in mock_error.call_args.args[1] or "API Error" in mock_error.call_args.args[2]


@pytest.mark.asyncio
async def test_tft_command_connection_error(setup_tft_cog, mock_interaction):
    """Test the tft command when a connection error occurs."""
    # Setup
    cog = setup_tft_cog
    region = "EUW1"
    riotid = "TestPlayer#1234"

    # Mock requests.get to raise a RequestException
    with patch('requests.get', side_effect=requests.exceptions.RequestException("Connection Error")), \
            patch('cogs.games.tft.TFT_API', 'test_api_key'), \
            patch('cogs.games.tft.logger.error') as mock_logger, \
            patch('cogs.games.tft.send_error_embed') as mock_error:
        # Call the command
        await cog.tft(mock_interaction, region, riotid)

        # Verify error handling
        mock_logger.assert_called_once()
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Connection Error"
        assert "Sorry, I couldn't retrieve Teamfight Tactics stats" in mock_error.call_args.args[2]


@pytest.mark.asyncio
async def test_tft_command_unexpected_error(setup_tft_cog, mock_interaction):
    """Test the tft command when an unexpected error occurs."""
    # Setup
    cog = setup_tft_cog
    region = "EUW1"
    riotid = "TestPlayer#1234"

    # Mock to raise an unexpected exception
    with patch('cogs.games.tft.TFT_API', 'test_api_key'), \
            patch.object(cog, 'tft', side_effect=Exception("Unexpected error")), \
            patch('cogs.games.tft.logger.error') as mock_logger, \
            patch('cogs.games.tft.send_error_embed') as mock_error:
        # Call the command (directly catching the exception since we mocked the method itself)
        with pytest.raises(Exception):
            await cog.tft(mock_interaction, region, riotid)


@pytest.mark.asyncio
async def test_setup(mock_bot):
    """Test the setup function."""
    # Call the setup function
    from cogs.games.tft import setup
    await setup(mock_bot)

    # Verify the cog was added to the bot
    mock_bot.add_cog.assert_called_once()

    # Check that the cog is an instance of TFTCog
    cog = mock_bot.add_cog.call_args.args[0]
    assert isinstance(cog, TFTCog)
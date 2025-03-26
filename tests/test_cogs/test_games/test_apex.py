import pytest
import discord
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from cogs.games.apex import ApexCog
from discord.ext import commands


@pytest.fixture
def setup_apex_cog(mock_bot):
    """Create an instance of the ApexCog."""
    return ApexCog(mock_bot)


@pytest.mark.asyncio
async def test_apex_command_success(setup_apex_cog, mock_interaction, mock_apex_response):
    """Test the apex command when the API call succeeds."""
    # Setup
    cog = setup_apex_cog
    platform = "Origin (PC)"
    name = "TestPlayer"

    # Mock the API function
    with patch('cogs.games.apex.fetch_apex_stats', return_value=mock_apex_response), \
            patch('cogs.games.apex.get_conditional_embed', return_value=None), \
            patch('asyncio.to_thread', AsyncMock(side_effect=lambda func, *args: func(*args))):
        # Call the command
        await cog.apex(mock_interaction, platform, name)

        # Verify deferred response
        mock_interaction.response.defer.assert_called_once()

        # Verify the API was called with the right parameters
        asyncio.to_thread.assert_called_once()
        call = asyncio.to_thread.call_args
        assert call.args[0] == fetch_apex_stats
        assert call.args[1] == platform
        assert call.args[2] == name

        # Verify followup.send was called with embeds
        mock_interaction.followup.send.assert_called_once()
        called_with_kwargs = mock_interaction.followup.send.call_args[1]
        assert 'embeds' in called_with_kwargs

        # Check that there's at least one embed
        embeds = called_with_kwargs['embeds']
        assert len(embeds) >= 1

        # Check the main embed's content
        main_embed = embeds[0]
        assert name in main_embed.title
        assert isinstance(main_embed, discord.Embed)


@pytest.mark.asyncio
async def test_apex_command_no_name(setup_apex_cog, mock_interaction):
    """Test the apex command when no name is provided."""
    # Setup
    cog = setup_apex_cog
    platform = "Origin (PC)"
    name = ""

    # Mock the send_error_embed function
    with patch('cogs.games.apex.send_error_embed') as mock_error:
        # Call the command
        await cog.apex(mock_interaction, platform, name)

        # Verify error handling
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Missing Username"


@pytest.mark.asyncio
async def test_apex_command_api_error(setup_apex_cog, mock_interaction):
    """Test the apex command when the API call raises an exception."""
    # Setup
    cog = setup_apex_cog
    platform = "Origin (PC)"
    name = "TestPlayer"

    # Mock the API function to raise an exception
    with patch('cogs.games.apex.fetch_apex_stats', side_effect=Exception("API Error")), \
            patch('cogs.games.apex.send_error_embed') as mock_error, \
            patch('cogs.games.apex.logger.error') as mock_logger, \
            patch('asyncio.to_thread', AsyncMock(side_effect=Exception("API Error"))):
        # Call the command
        await cog.apex(mock_interaction, platform, name)

        # Verify error handling
        mock_logger.assert_called_once()
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "API Error"


@pytest.mark.asyncio
async def test_apex_command_no_data(setup_apex_cog, mock_interaction):
    """Test the apex command when no data is returned."""
    # Setup
    cog = setup_apex_cog
    platform = "Origin (PC)"
    name = "TestPlayer"

    # Mock the API function to return empty data
    with patch('cogs.games.apex.fetch_apex_stats', return_value={}), \
            patch('cogs.games.apex.send_error_embed') as mock_error, \
            patch('asyncio.to_thread', AsyncMock(side_effect=lambda func, *args: func(*args))):
        # Call the command
        await cog.apex(mock_interaction, platform, name)

        # Verify error handling
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Account Not Found"


@pytest.mark.asyncio
async def test_apex_command_no_segments(setup_apex_cog, mock_interaction):
    """Test the apex command when the data has no segments."""
    # Setup
    cog = setup_apex_cog
    platform = "Origin (PC)"
    name = "TestPlayer"

    # Mock the API function to return data with no segments
    no_segments_data = {"data": {"segments": []}}
    with patch('cogs.games.apex.fetch_apex_stats', return_value=no_segments_data), \
            patch('cogs.games.apex.send_error_embed') as mock_error, \
            patch('asyncio.to_thread', AsyncMock(side_effect=lambda func, *args: func(*args))):
        # Call the command
        await cog.apex(mock_interaction, platform, name)

        # Verify error handling
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "No Data Available"


def test_build_embed(setup_apex_cog, mock_apex_response):
    """Test the build_embed method."""
    # Setup
    cog = setup_apex_cog
    name = "TestPlayer"
    platform = "Origin (PC)"

    # Extract data from the mock response
    segments = mock_apex_response['data']['segments']
    lifetime = segments[0]['stats']
    ranked = lifetime.get('rankScore', {})
    peak_rank = lifetime.get('lifetimePeakRankScore', {})
    active_legend_data = segments[0]

    # Call the method
    embed = cog.build_embed(name, platform, active_legend_data, lifetime, ranked, peak_rank)

    # Check the embed's properties
    assert isinstance(embed, discord.Embed)
    assert name in embed.title
    assert embed.timestamp is not None

    # Check that the embed has the required fields
    field_names = [field.name for field in embed.fields]
    assert "Lifetime Stats" in field_names
    assert "Current Rank" in field_names
    assert "Peak Rank" in field_names
    assert "Wraith - Currently Selected" in field_names
    assert "Support Us ❤️" in field_names

    # Check that the embed has the correct footer
    assert "Built By Goldiez" in embed.footer.text


def test_format_lifetime_stats(setup_apex_cog):
    """Test the format_lifetime_stats method."""
    # Setup
    cog = setup_apex_cog
    lifetime = {
        'level': {'value': 100, 'percentile': 75},
        'kills': {'value': 1000, 'percentile': 80},
        'damage': {'value': 300000, 'percentile': 75},
        'matchesPlayed': {'value': 2000, 'percentile': 70},
        'arenaWinStreak': {'value': 10, 'percentile': 90}
    }

    # Call the method
    result = cog.format_lifetime_stats(lifetime)

    # Check the result
    assert isinstance(result, str)
    assert "Level: **100 (Top 75%)**" in result
    assert "Kills: **1,000 (Top 80%)**" in result
    assert "Damage: **300,000 (Top 75%)**" in result
    assert "Matches Played: **2,000 (Top 70%)**" in result
    assert "Arena Winstreak: **10 (Top 90%)**" in result


def test_format_ranked_stats(setup_apex_cog):
    """Test the format_ranked_stats method."""
    # Setup
    cog = setup_apex_cog

    # Test with percentile
    ranked = {
        'metadata': {'rankName': 'Platinum'},
        'value': 7200,
        'percentile': 60
    }
    result = cog.format_ranked_stats(ranked)
    assert result == "**Platinum**: 7,200 (Top 60%)"

    # Test without percentile
    ranked = {
        'metadata': {'rankName': 'Gold'},
        'value': 5600
    }
    result = cog.format_ranked_stats(ranked)
    assert result == "**Gold**: 5,600 "

    # Test with zero percentile
    ranked = {
        'metadata': {'rankName': 'Bronze'},
        'value': 1200,
        'percentile': 0
    }
    result = cog.format_ranked_stats(ranked)
    assert result == "**Bronze**: 1,200 "


def test_format_peak_rank(setup_apex_cog):
    """Test the format_peak_rank method."""
    # Setup
    cog = setup_apex_cog

    # Test with valid data
    peak_rank = {
        'metadata': {'rankName': 'Diamond'},
        'value': 10000
    }
    result = cog.format_peak_rank(peak_rank)
    assert result == "**Diamond**: 10,000"

    # Test with missing metadata
    peak_rank = {'value': 8000}
    result = cog.format_peak_rank(peak_rank)
    assert result == "**Unknown**: 8,000"

    # Test with missing value
    peak_rank = {'metadata': {'rankName': 'Platinum'}}
    result = cog.format_peak_rank(peak_rank)
    assert result == "**Platinum**: 0"


def test_format_active_legend_stats(setup_apex_cog):
    """Test the format_active_legend_stats method."""
    # Setup
    cog = setup_apex_cog
    stats = {
        'kills': {'displayName': 'Kills', 'value': 1000},
        'damage': {'displayName': 'Damage', 'value': 300000},
        'headshots': {'displayName': 'Headshots', 'value': 500}
    }

    # Call the method
    result = cog.format_active_legend_stats(stats)

    # Check the result
    assert isinstance(result, str)
    assert "Kills: **1000**" in result
    assert "Damage: **300000**" in result
    assert "Headshots: **500**" in result


@pytest.mark.asyncio
async def test_setup(mock_bot):
    """Test the setup function."""
    # Call the setup function
    from cogs.games.apex import setup
    await setup(mock_bot)

    # Verify the cog was added to the bot
    mock_bot.add_cog.assert_called_once()

    # Check that the cog is an instance of ApexCog
    cog = mock_bot.add_cog.call_args.args[0]
    assert isinstance(cog, ApexCog)
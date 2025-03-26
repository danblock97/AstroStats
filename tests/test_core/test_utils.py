import pytest
import discord
import os
from unittest.mock import patch
from core.utils import get_conditional_embed, create_timestamp, create_progress_bar


@pytest.mark.asyncio
async def test_get_conditional_embed_with_content(mock_interaction):
    # Mock os.getenv to return a specific value
    with patch('os.getenv', return_value="Test embed content"):
        # Call the function
        embed = await get_conditional_embed(mock_interaction, "TEST_EMBED", discord.Color.blue())

        # Verify the result
        assert embed is not None
        assert embed.description == "Test embed content"
        assert embed.color == discord.Color.blue()


@pytest.mark.asyncio
async def test_get_conditional_embed_without_content(mock_interaction):
    # Mock os.getenv to return None
    with patch('os.getenv', return_value=None):
        # Call the function
        embed = await get_conditional_embed(mock_interaction, "TEST_EMBED", discord.Color.blue())

        # Verify the result
        assert embed is None


def test_create_timestamp():
    # Call the function
    timestamp = create_timestamp()

    # Verify the result is a datetime object with UTC timezone
    assert timestamp.tzinfo is not None
    assert timestamp.tzinfo.tzname(timestamp) == 'UTC'


def test_create_progress_bar():
    # Test with default parameters
    bar1 = create_progress_bar(5, 10)
    assert bar1 == "█████░░░░░"

    # Test with custom length and characters
    bar2 = create_progress_bar(3, 10, length=5, fill_char="X", empty_char="O")
    assert bar2 == "XXOOO"

    # Test with zero total (should avoid division by zero)
    bar3 = create_progress_bar(5, 0)
    assert bar3 == "██████████"  # Should be all filled

    # Test with current > total
    bar4 = create_progress_bar(15, 10)
    assert bar4 == "██████████"  # Should be all filled
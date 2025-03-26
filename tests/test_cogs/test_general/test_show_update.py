import pytest
import discord
from unittest.mock import patch, AsyncMock, MagicMock
from cogs.general.show_update import ShowUpdateCog


@pytest.fixture
def setup_show_update_cog(mock_bot):
    """Create an instance of the ShowUpdateCog."""
    return ShowUpdateCog(mock_bot)


@pytest.mark.asyncio
async def test_show_update_command_no_conditional_embed(setup_show_update_cog, mock_interaction):
    """Test the show_update command when no conditional embed is returned."""
    # Setup
    cog = setup_show_update_cog

    # Mock the get_conditional_embed function
    with patch('cogs.general.show_update.get_conditional_embed', return_value=None), \
            patch('cogs.general.show_update.LATEST_UPDATES', 'Test latest updates'):

        # Call the command
        await cog.show_update(mock_interaction)

        # Verify response
        mock_interaction.response.send_message.assert_called_once()
        called_with_kwargs = mock_interaction.response.send_message.call_args[1]
        assert 'embeds' in called_with_kwargs

        # Check the embeds
        embeds = called_with_kwargs['embeds']
        assert len(embeds) == 1

        main_embed = embeds[0]
        assert "Latest Bot Updates" in main_embed.title
        assert "Test latest updates" in main_embed.description
        assert main_embed.color == discord.Color.blue()

        # Check the support field
        support_field = None
        for field in main_embed.fields:
            if field.name == "Support Us ❤️":
                support_field = field
                break

        assert support_field is not None
        assert "buymeacoffee.com" in support_field.value

        # Check the footer
        assert f"Requested by {mock_interaction.user.display_name}" in main_embed.footer.text


@pytest.mark.asyncio
async def test_show_update_command_with_conditional_embed(setup_show_update_cog, mock_interaction):
    """Test the show_update command when a conditional embed is returned."""
    # Setup
    cog = setup_show_update_cog

    # Mock the get_conditional_embed function to return an embed
    conditional_embed = discord.Embed(description="Conditional embed content", color=discord.Color.orange())

    with patch('cogs.general.show_update.get_conditional_embed', return_value=conditional_embed), \
            patch('cogs.general.show_update.LATEST_UPDATES', 'Test latest updates'):
        # Call the command
        await cog.show_update(mock_interaction)

        # Verify response
        mock_interaction.response.send_message.assert_called_once()
        called_with_kwargs = mock_interaction.response.send_message.call_args[1]
        assert 'embeds' in called_with_kwargs

        # Check the embeds
        embeds = called_with_kwargs['embeds']
        assert len(embeds) == 2

        main_embed = embeds[0]
        assert "Latest Bot Updates" in main_embed.title

        cond_embed = embeds[1]
        assert cond_embed == conditional_embed
        assert "Conditional embed content" in cond_embed.description
        assert cond_embed.color == discord.Color.orange()


@pytest.mark.asyncio
async def test_setup(mock_bot):
    """Test the setup function."""
    # Call the setup function
    from cogs.general.show_update import setup
    await setup(mock_bot)

    # Verify the cog was added to the bot
    mock_bot.add_cog.assert_called_once()

    # Check that the cog is an instance of ShowUpdateCog
    cog = mock_bot.add_cog.call_args.args[0]
    assert isinstance(cog, ShowUpdateCog)
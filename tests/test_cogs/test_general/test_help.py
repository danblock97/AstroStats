import pytest
import discord
from unittest.mock import patch, AsyncMock, MagicMock
from cogs.general.help import HelpCog


@pytest.fixture
def setup_help_cog(mock_bot):
    """Create an instance of the HelpCog."""
    return HelpCog(mock_bot)


def test_build_help_embed(setup_help_cog):
    """Test the build_help_embed method."""
    # Setup
    cog = setup_help_cog
    guild_count = 100

    # Mock the guilds attribute
    cog.bot.guilds = [MagicMock() for _ in range(guild_count)]

    # Call the method
    embed = cog.build_help_embed()

    # Check the embed's properties
    assert isinstance(embed, discord.Embed)
    assert f"AstroStats Help & Support - Trusted by {guild_count} servers" in embed.title
    assert embed.color.value == 0xdd4f7a
    assert embed.timestamp is not None

    # Check the command fields
    command_field = None
    for field in embed.fields:
        if field.name == "Commands & Usage":
            command_field = field
            break

    assert command_field is not None
    # Verify various commands are present in the field value
    assert "/apex" in command_field.value
    assert "/league profile" in command_field.value
    assert "/tft" in command_field.value
    assert "/fortnite" in command_field.value
    assert "/horoscope" in command_field.value
    assert "/petbattles" in command_field.value

    # Check other fields
    apps_field = None
    for field in embed.fields:
        if field.name == "Check Out My Other Apps":
            apps_field = field
            break

    assert apps_field is not None
    assert "ClutchGG.LOL" in apps_field.value
    assert "Diverse Diaries" in apps_field.value
    assert "SwiftTasks" in apps_field.value

    support_field = None
    for field in embed.fields:
        if field.name == "Support":
            support_field = field
            break

    assert support_field is not None
    assert "AstroStats" in support_field.value

    # Check the footer
    assert "Built By Goldiez" in embed.footer.text


@pytest.mark.asyncio
async def test_help_command_no_conditional_embed(setup_help_cog, mock_interaction):
    """Test the help_command when no conditional embed is returned."""
    # Setup
    cog = setup_help_cog

    # Mock the build_help_embed method
    mock_embed = discord.Embed(title="Test Help Embed")
    with patch.object(cog, 'build_help_embed', return_value=mock_embed), \
            patch('cogs.general.help.get_conditional_embed', return_value=None):
        # Call the command
        await cog.help_command(mock_interaction)

        # Verify response
        mock_interaction.response.send_message.assert_called_once()
        called_with_kwargs = mock_interaction.response.send_message.call_args[1]
        assert 'embeds' in called_with_kwargs

        # Check the embeds
        embeds = called_with_kwargs['embeds']
        assert len(embeds) == 1
        assert embeds[0] == mock_embed


@pytest.mark.asyncio
async def test_help_command_with_conditional_embed(setup_help_cog, mock_interaction):
    """Test the help_command when a conditional embed is returned."""
    # Setup
    cog = setup_help_cog

    # Mock the build_help_embed method and conditional embed
    mock_main_embed = discord.Embed(title="Test Help Embed")
    mock_conditional_embed = discord.Embed(title="Conditional Embed")

    with patch.object(cog, 'build_help_embed', return_value=mock_main_embed), \
            patch('cogs.general.help.get_conditional_embed', return_value=mock_conditional_embed):
        # Call the command
        await cog.help_command(mock_interaction)

        # Verify response
        mock_interaction.response.send_message.assert_called_once()
        called_with_kwargs = mock_interaction.response.send_message.call_args[1]
        assert 'embeds' in called_with_kwargs

        # Check the embeds
        embeds = called_with_kwargs['embeds']
        assert len(embeds) == 2
        assert embeds[0] == mock_main_embed
        assert embeds[1] == mock_conditional_embed


@pytest.mark.asyncio
async def test_setup(mock_bot):
    """Test the setup function."""
    # Call the setup function
    from cogs.general.help import setup
    await setup(mock_bot)

    # Verify the cog was added to the bot
    mock_bot.add_cog.assert_called_once()

    # Check that the cog is an instance of HelpCog
    cog = mock_bot.add_cog.call_args.args[0]
    assert isinstance(cog, HelpCog)
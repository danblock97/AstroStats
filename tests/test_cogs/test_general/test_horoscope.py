import pytest
import discord
from unittest.mock import patch, AsyncMock, MagicMock
from cogs.general.horoscope import HoroscopeCog, SIGNS
from discord.ext import commands
from discord import app_commands


@pytest.fixture
def setup_horoscope_cog(mock_bot):
    """Create an instance of the HoroscopeCog."""
    return HoroscopeCog(mock_bot)


@pytest.fixture
def mock_choice():
    """Create a mock app_commands.Choice."""
    choice = MagicMock(spec=app_commands.Choice)
    choice.name = "Aries"
    choice.value = "aries"
    return choice


@pytest.fixture
def mock_html_response():
    """Create a mock HTML response for the horoscope API."""
    return """
    <html>
        <body>
            <div class="main-horoscope">
                <p>This is your horoscope for today. Expect good things to happen!</p>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_star_rating_response():
    """Create a mock HTML response for the star rating API."""
    return """
    <html>
        <body>
            <div class="module-skin">
                <h3>Love <i class="icon-star-filled highlight"></i><i class="icon-star-filled highlight"></i><i class="icon-star-filled"></i></h3>
                <p>Your romantic prospects are looking up today.</p>
                <h3>Money <i class="icon-star-filled highlight"></i><i class="icon-star-filled"></i><i class="icon-star-filled"></i></h3>
                <p>Financial opportunities abound.</p>
            </div>
        </body>
    </html>
    """


@pytest.mark.asyncio
async def test_fetch_horoscope_text_success(setup_horoscope_cog, mock_html_response):
    """Test fetching horoscope text when the API call succeeds."""
    # Setup
    cog = setup_horoscope_cog
    sign = "aries"

    # Mock the aiohttp.ClientSession and response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=mock_html_response)

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session):
        # Call the method
        result = await cog.fetch_horoscope_text(sign)

        # Verify the API was called with the right URL
        mock_session.get.assert_called_once()
        url = mock_session.get.call_args.args[0]
        assert sign in url
        assert str(SIGNS[sign]['api']) in url

        # Check the result
        assert "This is your horoscope for today" in result
        assert "Expect good things to happen!" in result


@pytest.mark.asyncio
async def test_fetch_horoscope_text_not_found(setup_horoscope_cog):
    """Test fetching horoscope text when the API returns 404."""
    # Setup
    cog = setup_horoscope_cog
    sign = "aries"

    # Mock the aiohttp.ClientSession and response
    mock_response = AsyncMock()
    mock_response.status = 404

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session):
        # Call the method
        result = await cog.fetch_horoscope_text(sign)

        # Check the result
        assert result is None


@pytest.mark.asyncio
async def test_fetch_horoscope_text_error(setup_horoscope_cog):
    """Test fetching horoscope text when the API returns an error."""
    # Setup
    cog = setup_horoscope_cog
    sign = "aries"

    # Mock the aiohttp.ClientSession and response
    mock_response = AsyncMock()
    mock_response.status = 500

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session), \
            patch('cogs.general.horoscope.logger.error') as mock_logger:
        # Call the method
        result = await cog.fetch_horoscope_text(sign)

        # Verify error was logged
        mock_logger.assert_called_once()

        # Check the result
        assert result is None


@pytest.mark.asyncio
async def test_fetch_star_rating_success(setup_horoscope_cog, mock_star_rating_response):
    """Test fetching star ratings when the API call succeeds."""
    # Setup
    cog = setup_horoscope_cog
    sign = "aries"
    embed = discord.Embed(title="Test Embed")
    embed.add_field(name="Support Us ❤️", value="Support link")

    # Mock the aiohttp.ClientSession and response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=mock_star_rating_response)

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch('aiohttp.ClientSession', return_value=mock_session):
        # Call the method
        result = await cog.fetch_star_rating(sign, embed)

        # Verify the API was called with the right URL
        mock_session.get.assert_called_once()
        url = mock_session.get.call_args.args[0]
        assert sign in url

        # Check the result is the updated embed
        assert result is not None
        assert isinstance(result, discord.Embed)

        # Check that the embed has the star ratings field
        has_star_ratings = False
        for field in result.fields:
            if field.name == "Star Ratings":
                has_star_ratings = True
                assert "Love" in field.value
                assert "Money" in field.value
                assert "⭐⭐" in field.value  # Two highlighted stars for Love
                assert "Your romantic prospects" in field.value
                break

        assert has_star_ratings, "The embed should have a 'Star Ratings' field"

        # Check that the Support field is still there
        has_support = False
        for field in result.fields:
            if field.name == "Support Us ❤️":
                has_support = True
                break

        assert has_support, "The embed should still have the 'Support Us' field"


@pytest.mark.asyncio
async def test_build_horoscope_embed(setup_horoscope_cog):
    """Test building the horoscope embed."""
    # Setup
    cog = setup_horoscope_cog
    sign = "aries"
    horoscope_text = "This is your horoscope for today. Expect good things to happen!"

    # Call the method
    result = cog.build_horoscope_embed(sign, horoscope_text)

    # Check the result
    assert isinstance(result, discord.Embed)
    assert f"Horoscope for {SIGNS[sign]['display']}" in result.title
    assert result.color == SIGNS[sign]['color']

    # Check that the embed has the horoscope field
    has_horoscope = False
    for field in result.fields:
        if field.name == "Today's Horoscope":
            has_horoscope = True
            assert horoscope_text in field.value
            break

    assert has_horoscope, "The embed should have a 'Today's Horoscope' field"

    # Check that the support field is there
    has_support = False
    for field in result.fields:
        if field.name == "Support Us ❤️":
            has_support = True
            break

    assert has_support, "The embed should have a 'Support Us' field"

    # Check that the image URL is set
    assert sign in result.thumbnail.url


@pytest.mark.asyncio
async def test_horoscope_command_success(setup_horoscope_cog, mock_interaction, mock_choice):
    """Test the horoscope command when everything succeeds."""
    # Setup
    cog = setup_horoscope_cog
    sign_choice = mock_choice
    horoscope_text = "This is your horoscope for today. Expect good things to happen!"

    # Mock the embed
    mock_embed = discord.Embed(title="Test Embed")

    # Mock the methods
    with patch.object(cog, 'fetch_horoscope_text', return_value=horoscope_text), \
            patch.object(cog, 'build_horoscope_embed', return_value=mock_embed), \
            patch.object(cog, 'fetch_star_rating', return_value=mock_embed), \
            patch('cogs.general.horoscope.get_conditional_embed', return_value=None):
        # Call the command
        await cog.horoscope(mock_interaction, sign_choice)

        # Verify interaction.response.defer was called
        mock_interaction.response.defer.assert_called_once()

        # Verify the methods were called with the right parameters
        cog.fetch_horoscope_text.assert_called_once_with(sign_choice.value)
        cog.build_horoscope_embed.assert_called_once_with(sign_choice.value, horoscope_text)
        cog.fetch_star_rating.assert_called_once()

        # Verify followup.send was called with the right parameters
        mock_interaction.followup.send.assert_called_once()
        kwargs = mock_interaction.followup.send.call_args.kwargs
        assert 'embeds' in kwargs
        assert kwargs['embeds'] == [mock_embed]


@pytest.mark.asyncio
async def test_horoscope_command_text_not_available(setup_horoscope_cog, mock_interaction, mock_choice):
    """Test the horoscope command when the horoscope text is not available."""
    # Setup
    cog = setup_horoscope_cog
    sign_choice = mock_choice

    # Mock the methods
    with patch.object(cog, 'fetch_horoscope_text', return_value=None):
        # Call the command
        await cog.horoscope(mock_interaction, sign_choice)

        # Verify interaction.response.defer was called
        mock_interaction.response.defer.assert_called_once()

        # Verify the method was called with the right parameter
        cog.fetch_horoscope_text.assert_called_once_with(sign_choice.value)

        # Verify followup.send was called with an error embed
        mock_interaction.followup.send.assert_called_once()
        kwargs = mock_interaction.followup.send.call_args.kwargs
        assert 'embed' in kwargs
        error_embed = kwargs['embed']
        assert "Horoscope Not Available" in error_embed.title
        assert "couldn't retrieve the horoscope" in error_embed.description
        assert sign_choice.name in error_embed.description


@pytest.mark.asyncio
async def test_horoscope_command_exception(setup_horoscope_cog, mock_interaction, mock_choice):
    """Test the horoscope command when an exception occurs."""
    # Setup
    cog = setup_horoscope_cog
    sign_choice = mock_choice

    # Mock the method to raise an exception
    with patch.object(cog, 'fetch_horoscope_text', side_effect=Exception("Test error")), \
            patch('cogs.general.horoscope.logger.error') as mock_logger, \
            patch('cogs.general.horoscope.send_error_embed') as mock_error:
        # Call the command
        await cog.horoscope(mock_interaction, sign_choice)

        # Verify error was logged
        mock_logger.assert_called_once()

        # Verify error embed was sent
        mock_error.assert_called_once()
        assert mock_error.call_args.args[0] == mock_interaction
        assert mock_error.call_args.args[1] == "Command Error"


@pytest.mark.asyncio
async def test_setup(mock_bot):
    """Test the setup function."""
    # Call the setup function
    from cogs.general.horoscope import setup
    await setup(mock_bot)

    # Verify the cog was added to the bot
    mock_bot.add_cog.assert_called_once()

    # Check that the cog is an instance of HoroscopeCog
    cog = mock_bot.add_cog.call_args.args[0]
    assert isinstance(cog, HoroscopeCog)
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from cogs.general.cosmos import Cosmos
import discord
import time

@pytest.fixture
def cosmos_cog(mock_bot):
    return Cosmos(mock_bot)

@pytest.mark.asyncio
async def test_apod_success(cosmos_cog, mock_interaction):
    """Test successful APOD retrieval"""
    mock_data = {
        "title": "Test Image",
        "date": "2023-01-01",
        "explanation": "This is a test explanation that is long enough.",
        "url": "http://example.com/image.jpg",
        "hdurl": "http://example.com/hd_image.jpg",
        "copyright": "NASA"
    }

    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_data
        mock_get.return_value.__aenter__.return_value = mock_resp

        await cosmos_cog.apod.callback(cosmos_cog, mock_interaction)

        mock_interaction.response.defer.assert_called_once()
        mock_interaction.followup.send.assert_called_once()
        
        args, kwargs = mock_interaction.followup.send.call_args
        embed = kwargs['embed']
        
        assert embed.title == "🌌 Test Image"
        assert embed.image.url == "http://example.com/image.jpg"
        assert "NASA" in embed.footer.text

@pytest.mark.asyncio
async def test_apod_failure(cosmos_cog, mock_interaction):
    """Test APOD failure handling"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 429 # Rate Limit
        mock_get.return_value.__aenter__.return_value = mock_resp

        await cosmos_cog.apod.callback(cosmos_cog, mock_interaction)
        
        args, kwargs = mock_interaction.followup.send.call_args
        assert "rate limit exceeded" in args[0]

@pytest.mark.asyncio
async def test_iss_success(cosmos_cog, mock_interaction):
    """Test ISS location retrieval"""
    mock_data = {
        "iss_position": {"latitude": "10.0", "longitude": "20.0"},
        "timestamp": 1234567890
    }

    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_data
        mock_get.return_value.__aenter__.return_value = mock_resp

        await cosmos_cog.iss.callback(cosmos_cog, mock_interaction)

        mock_interaction.followup.send.assert_called_once()
        args, kwargs = mock_interaction.followup.send.call_args
        embed = kwargs['embed']
        
        assert embed.title == "🛰️ ISS Live Location"
        assert "10.0" in [f.value for f in embed.fields]

@pytest.mark.asyncio
async def test_people_success(cosmos_cog, mock_interaction):
    """Test People in Space retrieval"""
    mock_data = {
        "number": 2,
        "people": [
            {"name": "Alice", "craft": "ISS"},
            {"name": "Bob", "craft": "ISS"}
        ]
    }

    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_data
        mock_get.return_value.__aenter__.return_value = mock_resp

        await cosmos_cog.astronauts.callback(cosmos_cog, mock_interaction)

        mock_interaction.followup.send.assert_called_once()
        args, kwargs = mock_interaction.followup.send.call_args
        embed = kwargs['embed']
        
        assert "People in Space: 2" in embed.title
        field_value = embed.fields[0].value
        assert "Alice" in field_value
        assert "Bob" in field_value

@pytest.mark.asyncio
async def test_launch_success_and_cache(cosmos_cog, mock_interaction):
    """Test Launch retrieval and caching logic"""
    mock_data = {
        "results": [{
            "name": "Falcon 9",
            "status": {"name": "Go"},
            "mission": {"description": "Test Mission"},
            "launch_service_provider": {"name": "SpaceX"},
            "pad": {"name": "LC-39A", "location": {"name": "KSC"}},
            "net": "2024-01-01T12:00:00Z",
            "image": "http://example.com/rocket.jpg"
        }]
    }

    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_data
        mock_get.return_value.__aenter__.return_value = mock_resp

        # First API call
        await cosmos_cog.launch.callback(cosmos_cog, mock_interaction)
        assert mock_get.call_count == 1
        
        args, kwargs = mock_interaction.followup.send.call_args
        embed = kwargs['embed']
        assert "Falcon 9" in embed.title

        # Create a new interaction for the second call
        mock_interaction2 = MagicMock(spec=discord.Interaction)
        mock_interaction2.response = AsyncMock()
        mock_interaction2.followup = AsyncMock()

        # Second call should use cache (no new API call)
        await cosmos_cog.launch.callback(cosmos_cog, mock_interaction2)
        assert mock_get.call_count == 1 # Verification of Cache
        
        mock_interaction2.followup.send.assert_called_once()

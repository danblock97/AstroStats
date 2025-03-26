import pytest
import requests
from unittest.mock import patch, MagicMock
from services.api.apex import fetch_apex_stats, get_percentile_label, format_stat_value
from core.errors import APIError, ResourceNotFoundError


@pytest.fixture
def mock_response():
    """Create a mock response object for testing."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"data": {"segments": [{"stats": {"kills": {"value": 1000}}}]}}
    return mock


def test_get_percentile_label():
    """Test the get_percentile_label function."""
    # Test for None
    assert get_percentile_label(None) == 'N/A'

    # Test for high percentile
    assert get_percentile_label(95) == '🌟 Top'
    assert get_percentile_label(90) == '🌟 Top'

    # Test for medium percentile
    assert get_percentile_label(75) == 'Top'
    assert get_percentile_label(50) == 'Top'

    # Test for low percentile
    assert get_percentile_label(45) == 'Bottom'
    assert get_percentile_label(10) == 'Bottom'


def test_format_stat_value():
    """Test the format_stat_value function."""
    # Test with value and percentile
    stat_data = {"value": 1000, "percentile": 75}
    assert format_stat_value(stat_data) == "1,000 (Top 75%)"

    # Test with value but no percentile
    stat_data = {"value": 1000}
    assert format_stat_value(stat_data) == "1,000 (Top 0%)"

    # Test with no value
    stat_data = {}
    assert format_stat_value(stat_data) == 'N/A'

    # Test with zero percentile
    stat_data = {"value": 1000, "percentile": 0}
    assert format_stat_value(stat_data) == "1,000 (Bottom 0%)"


def test_fetch_apex_stats_success(mock_response):
    """Test successful API call to fetch Apex stats."""
    platform = "Origin (PC)"
    name = "TestPlayer"

    # Mock the requests.get function
    with patch('services.api.apex.requests.get', return_value=mock_response), \
            patch('services.api.apex.TRN_API_KEY', 'test_key'):
        result = fetch_apex_stats(platform, name)

        # Check the result
        assert result == mock_response.json.return_value

        # Verify the API call
        requests.get.assert_called_once()
        url_arg = requests.get.call_args.args[0]
        assert "origin" in url_arg  # platform should be converted
        assert name in url_arg

        # Verify headers were set correctly
        headers_kwarg = requests.get.call_args.kwargs.get('headers')
        assert headers_kwarg == {"TRN-Api-Key": "test_key"}


def test_fetch_apex_stats_invalid_platform():
    """Test with invalid platform."""
    platform = "InvalidPlatform"
    name = "TestPlayer"

    with patch('services.api.apex.TRN_API_KEY', 'test_key'):
        # Should raise ValueError for invalid platform
        with pytest.raises(ValueError, match="Invalid platform"):
            fetch_apex_stats(platform, name)


def test_fetch_apex_stats_no_api_key():
    """Test with missing API key."""
    platform = "Origin (PC)"
    name = "TestPlayer"

    with patch('services.api.apex.TRN_API_KEY', None):
        # Should raise APIError for missing API key
        with pytest.raises(APIError, match="API key not configured"):
            fetch_apex_stats(platform, name)


def test_fetch_apex_stats_not_found():
    """Test when player is not found."""
    platform = "Origin (PC)"
    name = "TestPlayer"

    # Create a mock response for 404 Not Found
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch('services.api.apex.requests.get', return_value=mock_resp), \
            patch('services.api.apex.TRN_API_KEY', 'test_key'):
        # Should raise ResourceNotFoundError
        with pytest.raises(ResourceNotFoundError):
            fetch_apex_stats(platform, name)


def test_fetch_apex_stats_forbidden():
    """Test when API returns 403 Forbidden."""
    platform = "Origin (PC)"
    name = "TestPlayer"

    # Create a mock response for 403 Forbidden
    mock_resp = MagicMock()
    mock_resp.status_code = 403

    with patch('services.api.apex.requests.get', return_value=mock_resp), \
            patch('services.api.apex.TRN_API_KEY', 'test_key'), \
            patch('services.api.apex.logger.error') as mock_logger:
        # Should raise APIError
        with pytest.raises(APIError, match="Invalid API key or insufficient permissions"):
            fetch_apex_stats(platform, name)

        # Check that error was logged
        assert mock_logger.called


def test_fetch_apex_stats_other_status_code():
    """Test when API returns unexpected status code."""
    platform = "Origin (PC)"
    name = "TestPlayer"

    # Create a mock response with unexpected status code
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch('services.api.apex.requests.get', return_value=mock_resp), \
            patch('services.api.apex.TRN_API_KEY', 'test_key'), \
            patch('services.api.apex.logger.error') as mock_logger:
        # Should raise APIError
        with pytest.raises(APIError, match="API returned status code 500"):
            fetch_apex_stats(platform, name)

        # Check that error was logged
        assert mock_logger.called


def test_fetch_apex_stats_request_exception():
    """Test when requests.get raises an exception."""
    platform = "Origin (PC)"
    name = "TestPlayer"

    # Mock requests.get to raise an exception
    with patch('services.api.apex.requests.get', side_effect=requests.RequestException("Test error")), \
            patch('services.api.apex.TRN_API_KEY', 'test_key'), \
            patch('services.api.apex.logger.error') as mock_logger:
        # Should raise APIError
        with pytest.raises(APIError, match="Request error"):
            fetch_apex_stats(platform, name)

        # Check that error was logged
        assert mock_logger.called
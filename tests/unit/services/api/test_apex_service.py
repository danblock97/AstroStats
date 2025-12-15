import pytest
import requests
from unittest.mock import patch, MagicMock
from urllib.parse import quote


class TestApexAPIService:
    """Test Apex Legends API service functions"""
    
    @pytest.fixture
    def mock_response_success(self):
        """Mock successful API response"""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "platformInfo": {
                    "platformSlug": "origin",
                    "platformUserId": "test123",
                    "platformUserHandle": "TestPlayer",
                    "platformUserIdentifier": "TestPlayer",
                    "avatarUrl": "https://example.com/avatar.png"
                },
                "userInfo": {
                    "userId": 12345,
                    "isPremium": False,
                    "isVerified": False,
                    "isInfluencer": False,
                    "isPartner": False,
                    "countryCode": "US",
                    "customAvatarUrl": None,
                    "customHeroUrl": None,
                    "socialAccounts": []
                },
                "metadata": {},
                "segments": [
                    {
                        "type": "overview",
                        "attributes": {},
                        "metadata": {
                            "name": "Overview"
                        },
                        "expiryDate": "2024-12-01T00:00:00+00:00",
                        "stats": {
                            "level": {
                                "rank": None,
                                "percentile": None,
                                "displayName": "Level",
                                "displayCategory": "Combat",
                                "category": None,
                                "metadata": {},
                                "value": 150.0,
                                "displayValue": "150",
                                "displayType": "number"
                            },
                            "kills": {
                                "rank": 1234567,
                                "percentile": 75.5,
                                "displayName": "Kills",
                                "displayCategory": "Combat",
                                "category": None,
                                "metadata": {},
                                "value": 1500.0,
                                "displayValue": "1,500",
                                "displayType": "number"
                            }
                        }
                    }
                ]
            }
        }
        return response

    @pytest.fixture
    def mock_response_not_found(self):
        """Mock 404 not found response"""
        response = MagicMock()
        response.status_code = 404
        return response

    @pytest.fixture
    def mock_response_forbidden(self):
        """Mock 403 forbidden response"""
        response = MagicMock()
        response.status_code = 403
        return response

    @pytest.fixture
    def mock_response_server_error(self):
        """Mock 500 server error response"""
        response = MagicMock()
        response.status_code = 500
        return response

    def test_fetch_apex_stats_success(self, mock_response_success):
        """Test successful API call to fetch Apex stats"""
        from services.api.apex import fetch_apex_stats
        
        with patch('services.api.apex.TRN_API_KEY', 'test_api_key'):
            with patch('requests.get', return_value=mock_response_success) as mock_get:
                result = fetch_apex_stats("Origin (PC)", "TestPlayer")
                
                # Verify API call
                expected_url = "https://public-api.tracker.gg/v2/apex/standard/profile/origin/TestPlayer"
                expected_headers = {"TRN-Api-Key": "test_api_key"}
                
                mock_get.assert_called_once_with(expected_url, headers=expected_headers)
                
                # Verify result
                assert result == mock_response_success.json.return_value

    def test_fetch_apex_stats_player_not_found(self, mock_response_not_found):
        """Test API call when player is not found"""
        from services.api.apex import fetch_apex_stats
        from core.errors import ResourceNotFoundError
        
        with patch('services.api.apex.TRN_API_KEY', 'test_api_key'):
            with patch('requests.get', return_value=mock_response_not_found):
                with pytest.raises(ResourceNotFoundError, match="No Apex Legends stats found for TestPlayer on Origin \\(PC\\)"):
                    fetch_apex_stats("Origin (PC)", "TestPlayer")

    def test_fetch_apex_stats_invalid_api_key(self, mock_response_forbidden):
        """Test API call with invalid API key (403)"""
        from services.api.apex import fetch_apex_stats
        from core.errors import APIError
        
        with patch('services.api.apex.TRN_API_KEY', 'invalid_key'):
            with patch('requests.get', return_value=mock_response_forbidden):
                with pytest.raises(APIError, match="Invalid API key or insufficient permissions"):
                    fetch_apex_stats("Origin (PC)", "TestPlayer")

    def test_fetch_apex_stats_server_error(self, mock_response_server_error):
        """Test API call with server error"""
        from services.api.apex import fetch_apex_stats
        from core.errors import APIError
        
        with patch('services.api.apex.TRN_API_KEY', 'test_api_key'):
            with patch('requests.get', return_value=mock_response_server_error):
                with pytest.raises(APIError, match="API returned status code 500"):
                    fetch_apex_stats("Origin (PC)", "TestPlayer")

    def test_fetch_apex_stats_no_api_key(self):
        """Test API call when API key is not configured"""
        from services.api.apex import fetch_apex_stats
        from core.errors import APIError
        
        with patch('services.api.apex.TRN_API_KEY', None):
            with pytest.raises(APIError, match="API key not configured"):
                fetch_apex_stats("Origin (PC)", "TestPlayer")

    def test_fetch_apex_stats_invalid_platform(self):
        """Test API call with invalid platform"""
        from services.api.apex import fetch_apex_stats
        
        with patch('services.api.apex.TRN_API_KEY', 'test_api_key'):
            with pytest.raises(ValueError, match="Invalid platform: InvalidPlatform"):
                fetch_apex_stats("InvalidPlatform", "TestPlayer")

    def test_fetch_apex_stats_platform_mapping(self):
        """Test platform mapping works correctly"""
        from services.api.apex import fetch_apex_stats
        
        with patch('services.api.apex.TRN_API_KEY', 'test_api_key'):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {}
                mock_get.return_value = mock_response
                
                # Test all platform mappings
                platform_tests = [
                    ("Xbox", "xbl"),
                    ("Playstation", "psn"),
                    ("Origin (PC)", "origin")
                ]
                
                for display_platform, api_platform in platform_tests:
                    fetch_apex_stats(display_platform, "TestPlayer")
                    
                    # Check the URL contains correct platform
                    call_args = mock_get.call_args[0]
                    assert api_platform in call_args[0]

    def test_fetch_apex_stats_username_encoding(self):
        """Test username is properly URL encoded"""
        from services.api.apex import fetch_apex_stats
        
        with patch('services.api.apex.TRN_API_KEY', 'test_api_key'):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {}
                mock_get.return_value = mock_response
                
                # Test username with special characters
                special_username = "Test Player#1234"
                fetch_apex_stats("Origin (PC)", special_username)
                
                # Check URL contains encoded username
                call_args = mock_get.call_args[0]
                url = call_args[0]
                encoded_username = quote(special_username)
                assert encoded_username in url
                assert special_username not in url  # Original should not be in URL

    def test_fetch_apex_stats_request_exception(self):
        """Test handling of requests exceptions"""
        from services.api.apex import fetch_apex_stats
        from core.errors import APIError
        
        with patch('services.api.apex.TRN_API_KEY', 'test_api_key'):
            with patch('requests.get', side_effect=requests.RequestException("Network error")):
                with pytest.raises(APIError, match="Request error: Network error"):
                    fetch_apex_stats("Origin (PC)", "TestPlayer")

    def test_get_percentile_label_top_tier(self):
        """Test percentile label for top tier performance"""
        from services.api.apex import get_formatted_percentile
        
        # Top tier (>= 90th percentile) -> should show small Top X%
        assert get_formatted_percentile(95.0) == 'Top 5%'
        assert get_formatted_percentile(90.0) == 'Top 10%'
        
        # Special case for 100th percentile or very close
        assert get_formatted_percentile(99.9) == 'Top 0.1%'

    def test_get_percentile_label_above_average(self):
        """Test percentile label for above average performance"""
        from services.api.apex import get_formatted_percentile
        
        # Above average (50-89th percentile)
        assert get_formatted_percentile(75.0) == 'Top 25%'
        assert get_formatted_percentile(50.0) == 'Top 50%'
        assert get_formatted_percentile(89.0) == 'Top 11%'

    def test_get_percentile_label_below_average(self):
        """Test percentile label for below average performance"""
        from services.api.apex import get_formatted_percentile
        
        # Below average (< 50th percentile)
        assert get_formatted_percentile(25.0) == 'Bottom 25%'
        assert get_formatted_percentile(0.0) == 'Bottom 0%'
        assert get_formatted_percentile(49.0) == 'Bottom 49%'

    def test_get_percentile_label_none_value(self):
        """Test percentile label when value is None"""
        from services.api.apex import get_formatted_percentile
        
        assert get_formatted_percentile(None) == 'N/A'

    def test_format_stat_value_with_percentile(self):
        """Test stat value formatting with percentile"""
        from services.api.apex import format_stat_value
        
        stat_data = {
            'value': 1500.5,
            'percentile': 75.0
        }
        
        # 75th percentile -> Top 25%
        result = format_stat_value(stat_data)
        assert result == "1,500 (Top 25%)"

    def test_format_stat_value_top_tier(self):
        """Test stat value formatting for top tier performance"""
        from services.api.apex import format_stat_value
        
        stat_data = {
            'value': 2500,
            'percentile': 95.0
        }
        
        # 95th percentile -> Top 5%
        result = format_stat_value(stat_data)
        assert result == "2,500 (Top 5%)"

    def test_format_stat_value_no_percentile(self):
        """Test stat value formatting without percentile"""
        from services.api.apex import format_stat_value
        
        stat_data = {
            'value': 1000,
            'percentile': 0
        }
        
        result = format_stat_value(stat_data)
        assert result == "1,000 (Bottom 0%)"

    def test_format_stat_value_no_value(self):
        """Test stat value formatting when value is None"""
        from services.api.apex import format_stat_value
        
        stat_data = {}
        
        result = format_stat_value(stat_data)
        assert result == "N/A"

    def test_format_stat_value_none_percentile(self):
        """Test stat value formatting with None percentile"""
        from services.api.apex import format_stat_value
        
        stat_data = {
            'value': 800,
            'percentile': None
        }
        
        result = format_stat_value(stat_data)
        assert result == "800"

    def test_format_stat_value_decimal_handling(self):
        """Test stat value formatting handles decimals correctly"""
        from services.api.apex import format_stat_value
        
        stat_data = {
            'value': 1234.7,
            'percentile': 60.0
        }
        
        # 60th percentile -> Top 40%
        result = format_stat_value(stat_data)
        assert result == "1,234 (Top 40%)"

    def test_format_stat_value_large_numbers(self):
        """Test stat value formatting with large numbers"""
        from services.api.apex import format_stat_value
        
        stat_data = {
            'value': 1234567.0,
            'percentile': 85.0
        }
        
        # 85th percentile -> Top 15%
        result = format_stat_value(stat_data)
        assert result == "1,234,567 (Top 15%)"


    def test_api_constants_integration(self):
        """Test integration with constants for platform mapping"""
        from config.constants import APEX_PLATFORM_MAPPING
        from services.api.apex import fetch_apex_stats
        
        # Test that all platforms in mapping are valid
        for display_platform, api_platform in APEX_PLATFORM_MAPPING.items():
            assert isinstance(display_platform, str)
            assert isinstance(api_platform, str)
            assert len(display_platform) > 0
            assert len(api_platform) > 0

    def test_api_url_construction(self):
        """Test API URL is constructed correctly"""
        from services.api.apex import fetch_apex_stats
        
        with patch('services.api.apex.TRN_API_KEY', 'test_key'):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {}
                mock_get.return_value = mock_response
                
                fetch_apex_stats("Origin (PC)", "TestUser")
                
                # Check URL structure
                call_args = mock_get.call_args[0]
                url = call_args[0]
                
                assert url.startswith("https://public-api.tracker.gg/v2/apex/standard/profile/")
                assert "/origin/TestUser" in url

    def test_api_headers_structure(self):
        """Test API headers are structured correctly"""
        from services.api.apex import fetch_apex_stats
        
        with patch('services.api.apex.TRN_API_KEY', 'test_key_123'):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {}
                mock_get.return_value = mock_response
                
                fetch_apex_stats("Origin (PC)", "TestUser")
                
                # Check headers
                call_kwargs = mock_get.call_args[1]
                headers = call_kwargs['headers']
                
                assert 'TRN-Api-Key' in headers
                assert headers['TRN-Api-Key'] == 'test_key_123'

    def test_error_logging(self):
        """Test that errors are logged appropriately"""
        from services.api.apex import fetch_apex_stats
        
        with patch('services.api.apex.TRN_API_KEY', 'test_key'):
            with patch('requests.get') as mock_get:
                with patch('services.api.apex.logger') as mock_logger:
                    # Test 403 error logging
                    mock_response = MagicMock()
                    mock_response.status_code = 403
                    mock_get.return_value = mock_response
                    
                    try:
                        fetch_apex_stats("Origin (PC)", "TestUser")
                    except:
                        pass
                    
                    mock_logger.error.assert_called()

    def test_api_service_type_validation(self):
        """Test API service function parameter types"""
        from services.api.apex import fetch_apex_stats
        
        # Should accept string parameters
        with patch('services.api.apex.TRN_API_KEY', 'test_key'):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {}
                mock_get.return_value = mock_response
                
                # Should not raise type errors
                result = fetch_apex_stats("Origin (PC)", "TestUser")
                assert isinstance(result, dict)

    def test_percentile_edge_cases(self):
        """Test percentile calculation edge cases"""
        from services.api.apex import get_formatted_percentile
        
        # Test boundary values
        assert get_formatted_percentile(0.0) == 'Bottom 0%'
        assert get_formatted_percentile(49.0) == 'Bottom 49%'
        assert get_formatted_percentile(50.0) == 'Top 50%'
        assert get_formatted_percentile(89.0) == 'Top 11%'
        assert get_formatted_percentile(90.0) == 'Top 10%'
        assert get_formatted_percentile(100.0) == 'Top 0.1%'  # Special case: 0% becomes 0.1%

    def test_stat_formatting_edge_cases(self):
        """Test stat formatting with edge cases"""
        from services.api.apex import format_stat_value
        
        # Test zero value
        zero_stat = {'value': 0, 'percentile': 10.0}
        assert format_stat_value(zero_stat) == "0 (Bottom 10%)"
        
        # Test negative value (shouldn't happen but test gracefully)
        negative_stat = {'value': -1, 'percentile': 5.0}
        result = format_stat_value(negative_stat)
        assert "-1" in result

    def test_request_timeout_handling(self):
        """Test handling of request timeouts"""
        from services.api.apex import fetch_apex_stats
        from core.errors import APIError
        
        with patch('services.api.apex.TRN_API_KEY', 'test_key'):
            with patch('requests.get', side_effect=requests.Timeout("Request timed out")):
                with pytest.raises(APIError, match="Request error: Request timed out"):
                    fetch_apex_stats("Origin (PC)", "TestUser")

    def test_connection_error_handling(self):
        """Test handling of connection errors"""
        from services.api.apex import fetch_apex_stats
        from core.errors import APIError
        
        with patch('services.api.apex.TRN_API_KEY', 'test_key'):
            with patch('requests.get', side_effect=requests.ConnectionError("Connection failed")):
                with pytest.raises(APIError, match="Request error: Connection failed"):
                    fetch_apex_stats("Origin (PC)", "TestUser")

    def test_api_key_configuration_check(self):
        """Test API key configuration is checked before making requests"""
        from services.api.apex import fetch_apex_stats
        from core.errors import APIError
        
        # Test with empty string
        with patch('services.api.apex.TRN_API_KEY', ''):
            with pytest.raises(APIError, match="API key not configured"):
                fetch_apex_stats("Origin (PC)", "TestUser")
        
        # Test with None
        with patch('services.api.apex.TRN_API_KEY', None):
            with pytest.raises(APIError, match="API key not configured"):
                fetch_apex_stats("Origin (PC)", "TestUser")
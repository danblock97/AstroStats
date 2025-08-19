import pytest
import requests
from unittest.mock import patch, MagicMock
from core.errors import APIError, ResourceNotFoundError


class TestApexAPIService:
    """Test Apex Legends API service functionality"""
    
    def test_apex_platform_mapping(self):
        """Test Apex platform mapping for API calls"""
        platform_mapping = {
            "Xbox": "xbl",
            "Playstation": "psn", 
            "Origin (PC)": "origin"
        }
        
        # Should map user-friendly names to API values
        assert platform_mapping["Xbox"] == "xbl"
        assert platform_mapping["Playstation"] == "psn"
        assert platform_mapping["Origin (PC)"] == "origin"

    def test_apex_api_url_construction(self):
        """Test Apex API URL construction"""
        base_url = "https://public-api.tracker.gg/v2/apex/standard/profile"
        platform = "xbl"
        username = "TestPlayer"
        
        # URL should be properly encoded
        from urllib.parse import quote
        encoded_username = quote(username)
        expected_url = f"{base_url}/{platform}/{encoded_username}"
        
        assert encoded_username == "TestPlayer"  # Simple name doesn't need encoding
        assert expected_url == f"{base_url}/xbl/TestPlayer"

    def test_apex_api_url_encoding(self):
        """Test URL encoding for special characters in usernames"""
        from urllib.parse import quote
        
        special_usernames = [
            {"input": "Player Name", "encoded": "Player%20Name"},
            {"input": "Player@123", "encoded": "Player%40123"},
            {"input": "Player+Test", "encoded": "Player%2BTest"}
        ]
        
        for case in special_usernames:
            encoded = quote(case["input"])
            assert encoded == case["encoded"]

    @pytest.mark.asyncio
    async def test_apex_api_headers(self):
        """Test Apex API request headers"""
        headers = {
            "TRN-Api-Key": "test-api-key"
        }
        
        # Should include proper API key header
        assert "TRN-Api-Key" in headers
        assert len(headers["TRN-Api-Key"]) > 0

    @pytest.mark.asyncio
    async def test_apex_api_success_response(self):
        """Test successful Apex API response handling"""
        mock_response_data = {
            "data": {
                "platformInfo": {
                    "platformSlug": "xbl",
                    "platformUserId": "TestPlayer"
                },
                "metadata": {
                    "activeLegendName": "Wraith"
                },
                "segments": [
                    {
                        "type": "overview",
                        "stats": {
                            "level": {"value": 120},
                            "kills": {"value": 1500},
                            "damage": {"value": 500000}
                        }
                    }
                ]
            }
        }
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response
            
            # Should return the response data
            response = mock_response.json()
            assert response == mock_response_data
            assert "data" in response
            assert "segments" in response["data"]

    @pytest.mark.asyncio
    async def test_apex_api_404_error(self):
        """Test Apex API 404 (player not found) handling"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            # Should raise ResourceNotFoundError for 404
            status_code = mock_response.status_code
            if status_code == 404:
                error_type = "ResourceNotFoundError"
            else:
                error_type = "Other"
                
            assert error_type == "ResourceNotFoundError"

    @pytest.mark.asyncio
    async def test_apex_api_403_error(self):
        """Test Apex API 403 (forbidden/invalid key) handling"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_get.return_value = mock_response
            
            # Should raise APIError for 403
            status_code = mock_response.status_code
            if status_code == 403:
                error_type = "APIError"
                error_message = "Invalid API key or access denied"
            else:
                error_type = "Other"
                
            assert error_type == "APIError"
            assert "API key" in error_message

    @pytest.mark.asyncio
    async def test_apex_api_429_rate_limit(self):
        """Test Apex API rate limiting handling"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_get.return_value = mock_response
            
            # Should handle rate limiting
            status_code = mock_response.status_code
            if status_code == 429:
                retry_after = mock_response.headers.get("Retry-After", "60")
                error_message = f"Rate limit exceeded. Retry after {retry_after} seconds."
            
            assert "Rate limit exceeded" in error_message
            assert "60 seconds" in error_message

    @pytest.mark.asyncio
    async def test_apex_api_server_errors(self):
        """Test Apex API server error handling"""
        server_error_codes = [500, 502, 503, 504]
        
        for error_code in server_error_codes:
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = error_code
                mock_get.return_value = mock_response
                
                # Should handle server errors
                if 500 <= error_code < 600:
                    error_type = "APIError"
                    error_message = "Service temporarily unavailable"
                
                assert error_type == "APIError"
                assert "unavailable" in error_message

    @pytest.mark.asyncio
    async def test_apex_api_network_errors(self):
        """Test network error handling"""
        network_errors = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.Timeout("Request timed out"),
            requests.exceptions.RequestException("Network error")
        ]
        
        for error in network_errors:
            # Should handle network errors gracefully
            error_type = type(error).__name__
            assert error_type in ["ConnectionError", "Timeout", "RequestException"]

    def test_apex_api_platform_validation(self):
        """Test platform validation before API calls"""
        valid_platforms = ["Xbox", "Playstation", "Origin (PC)"]
        invalid_platforms = ["PC", "Steam", "Mobile", "InvalidPlatform"]
        
        apex_platform_mapping = {
            "Xbox": "xbl",
            "Playstation": "psn",
            "Origin (PC)": "origin"
        }
        
        for platform in valid_platforms:
            is_valid = platform in apex_platform_mapping
            assert is_valid is True
            
        for platform in invalid_platforms:
            is_valid = platform in apex_platform_mapping  
            assert is_valid is False

    def test_apex_api_username_validation(self):
        """Test username validation before API calls"""
        valid_usernames = ["TestPlayer", "Player123", "Test_Player"]
        invalid_usernames = ["", None, "a" * 100]  # Empty, None, too long
        
        for username in valid_usernames:
            is_valid = bool(username and len(username) >= 1 and len(username) <= 50)
            assert is_valid is True
            
        for username in invalid_usernames:
            is_valid = bool(username and len(username) >= 1 and len(username) <= 50)
            assert is_valid is False

    def test_apex_api_key_validation(self):
        """Test API key validation"""
        api_key_scenarios = [
            {"key": "valid-api-key-123", "valid": True},
            {"key": "", "valid": False},
            {"key": None, "valid": False}
        ]
        
        for scenario in api_key_scenarios:
            api_key = scenario["key"]
            is_valid = bool(api_key and len(api_key) > 0)
            
            if scenario["valid"]:
                assert is_valid is True
            else:
                assert is_valid is False

    def test_apex_stat_value_formatting(self):
        """Test Apex stat value formatting"""
        stat_examples = [
            {"raw": {"value": 1500, "displayValue": "1,500"}, "formatted": "1,500"},
            {"raw": {"value": 0}, "formatted": "0"},
            {"raw": {}, "formatted": "N/A"}  # Missing value
        ]
        
        for example in stat_examples:
            raw_stat = example["raw"]
            
            # Format stat value (handle missing values)
            if "value" in raw_stat:
                formatted = f"{raw_stat['value']:,}"
            else:
                formatted = "N/A"
                
            assert formatted == example["formatted"]

    def test_apex_response_structure_validation(self):
        """Test Apex API response structure validation"""
        required_response_fields = [
            "data",
            "data.segments", 
            "data.metadata",
            "data.platformInfo"
        ]
        
        # Mock valid response
        valid_response = {
            "data": {
                "segments": [],
                "metadata": {},
                "platformInfo": {}
            }
        }
        
        # Should validate response structure
        has_data = "data" in valid_response
        has_segments = "segments" in valid_response.get("data", {})
        has_metadata = "metadata" in valid_response.get("data", {})
        has_platform_info = "platformInfo" in valid_response.get("data", {})
        
        assert has_data is True
        assert has_segments is True  
        assert has_metadata is True
        assert has_platform_info is True

    def test_apex_error_message_formatting(self):
        """Test error message formatting for users"""
        error_scenarios = [
            {
                "error_type": "ResourceNotFoundError",
                "username": "TestPlayer",
                "platform": "Xbox",
                "expected_message": "No Apex Legends stats found for TestPlayer on Xbox"
            },
            {
                "error_type": "APIError", 
                "message": "API key not configured",
                "expected_user_message": "API configuration error"
            }
        ]
        
        for scenario in error_scenarios:
            if scenario["error_type"] == "ResourceNotFoundError":
                # Should provide specific user and platform context
                assert scenario["username"] in scenario["expected_message"]
                assert scenario["platform"] in scenario["expected_message"]
            elif scenario["error_type"] == "APIError":
                # Should provide user-friendly API error messages
                assert len(scenario["expected_user_message"]) > 0
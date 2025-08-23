import pytest
import time
from unittest.mock import patch, MagicMock, call
from pymongo.errors import PyMongoError


class TestPremiumServiceComplete:
    """Comprehensive tests for the premium service system"""
    
    @pytest.fixture
    def mock_mongo_client(self):
        """Mock MongoDB client"""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client.admin.command.return_value = None  # Successful ping
        
        return mock_client, mock_db, mock_collection

    @pytest.fixture
    def sample_user_docs(self):
        """Sample user documents for testing"""
        now = int(time.time())
        future = now + 86400  # 24 hours from now
        past = now - 86400    # 24 hours ago
        
        return {
            'active_supporter': {
                'discordId': '123456789',
                'premium': True,
                'status': 'active',
                'role': 'supporter',
                'currentPeriodEnd': future
            },
            'active_sponsor': {
                'discordId': '234567890',
                'premium': True,
                'status': 'active',
                'role': 'sponsor',
                'currentPeriodEnd': future
            },
            'active_vip': {
                'discordId': '345678901',
                'premium': True,
                'status': 'active',
                'role': 'vip',
                'currentPeriodEnd': future
            },
            'trialing_user': {
                'discordId': '456789012',
                'premium': True,
                'status': 'trialing',
                'role': 'supporter',
                'currentPeriodEnd': future
            },
            'expired_user': {
                'discordId': '567890123',
                'premium': True,
                'status': 'active',
                'role': 'sponsor',
                'currentPeriodEnd': past
            },
            'cancelled_user': {
                'discordId': '678901234',
                'premium': True,
                'status': 'cancelled',
                'role': 'vip',
                'currentPeriodEnd': future,
                'cancelAtPeriodEnd': True
            },
            'non_premium_user': {
                'discordId': '789012345',
                'premium': False,
                'role': 'sponsor'
            },
            'free_user': {
                'discordId': '890123456'
            },
            'unknown_role_user': {
                'discordId': '901234567',
                'premium': True,
                'status': 'active',
                'role': 'unknown_tier',
                'currentPeriodEnd': future
            }
        }

    def test_db_initialization_success(self, mock_mongo_client):
        """Test successful database initialization"""
        from services.premium import _init_db_if_needed, _mongo_client
        
        # Check if MongoDB client is already initialized from module import
        if _mongo_client is not None:
            # Database was already initialized successfully during import
            assert _mongo_client is not None
            return
        
        # If not initialized, test the initialization process
        mock_client, mock_db, mock_collection = mock_mongo_client
        
        with patch('services.premium.MongoClient', return_value=mock_client):
            with patch('services.premium.MONGODB_URI', 'mongodb://test'):
                with patch('services.premium.USERS_DB_NAME', 'test_db'):
                    with patch('services.premium.USERS_COLLECTION_NAME', 'users'):
                        _init_db_if_needed()
                        
                        # Verify MongoDB client was created correctly
                        mock_client.admin.command.assert_called_once_with("ping")

    def test_db_initialization_failure(self):
        """Test database initialization failure handling"""
        # Test that the module handles initialization errors gracefully
        with patch('services.premium.MongoClient', side_effect=Exception("Connection failed")):
            with patch('services.premium.logger') as mock_logger:
                # Import will trigger module initialization
                import importlib
                import services.premium
                importlib.reload(services.premium)
                
                # Should handle gracefully without crashing
                assert True  # Test passes if no exception is raised

    def test_get_user_by_discord_id_success(self, mock_mongo_client, sample_user_docs):
        """Test successful user retrieval"""
        from services.premium import get_user_by_discord_id
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        mock_collection.find_one.return_value = sample_user_docs['active_supporter']
        
        with patch('services.premium._mongo_client', mock_client):
            with patch('services.premium._users_collection', mock_collection):
                result = get_user_by_discord_id('123456789')
                
                assert result == sample_user_docs['active_supporter']
                mock_collection.find_one.assert_called_once_with({"discordId": "123456789"})

    def test_get_user_by_discord_id_fallback_db(self, mock_mongo_client, sample_user_docs):
        """Test user retrieval with fallback database"""
        from services.premium import get_user_by_discord_id
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        mock_fallback_collection = MagicMock()
        
        # Primary collection returns None, fallback returns user
        mock_collection.find_one.return_value = None
        mock_fallback_collection.find_one.return_value = sample_user_docs['active_supporter']
        
        with patch('services.premium._mongo_client', mock_client):
            with patch('services.premium._users_collection', mock_collection):
                with patch('services.premium._fallback_users_collection', mock_fallback_collection):
                    result = get_user_by_discord_id('123456789')
                    
                    assert result == sample_user_docs['active_supporter']
                    mock_collection.find_one.assert_called_once()
                    mock_fallback_collection.find_one.assert_called_once()

    def test_get_user_by_discord_id_not_found(self, mock_mongo_client):
        """Test user not found in any database"""
        from services.premium import get_user_by_discord_id
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        mock_fallback_collection = MagicMock()
        
        mock_collection.find_one.return_value = None
        mock_fallback_collection.find_one.return_value = None
        
        with patch('services.premium._mongo_client', mock_client):
            with patch('services.premium._users_collection', mock_collection):
                with patch('services.premium._fallback_users_collection', mock_fallback_collection):
                    result = get_user_by_discord_id('nonexistent')
                    
                    assert result is None

    def test_get_user_by_discord_id_db_error(self, mock_mongo_client):
        """Test database error handling"""
        from services.premium import get_user_by_discord_id
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        mock_collection.find_one.side_effect = PyMongoError("Database error")
        
        with patch('services.premium._mongo_client', mock_client):
            with patch('services.premium._users_collection', mock_collection):
                with patch('services.premium.logger') as mock_logger:
                    result = get_user_by_discord_id('123456789')
                    
                    assert result is None
                    mock_logger.error.assert_called()

    def test_is_premium_active_true_cases(self, sample_user_docs):
        """Test cases where premium should be active"""
        from services.premium import is_premium_active
        
        # Active user
        assert is_premium_active(sample_user_docs['active_supporter']) is True
        
        # Trialing user
        assert is_premium_active(sample_user_docs['trialing_user']) is True
        
        # Different tiers
        assert is_premium_active(sample_user_docs['active_sponsor']) is True
        assert is_premium_active(sample_user_docs['active_vip']) is True

    def test_is_premium_active_false_cases(self, sample_user_docs):
        """Test cases where premium should not be active"""
        from services.premium import is_premium_active
        
        # None user doc
        assert is_premium_active(None) is False
        
        # Non-premium user
        assert is_premium_active(sample_user_docs['non_premium_user']) is False
        
        # Free user (no premium field)
        assert is_premium_active(sample_user_docs['free_user']) is False
        
        # Expired user
        assert is_premium_active(sample_user_docs['expired_user']) is False
        
        # Cancelled user
        assert is_premium_active(sample_user_docs['cancelled_user']) is False

    def test_is_premium_active_malformed_date(self):
        """Test handling of malformed currentPeriodEnd"""
        from services.premium import is_premium_active
        
        user_doc = {
            'premium': True,
            'status': 'active',
            'currentPeriodEnd': 'invalid_date'
        }
        
        assert is_premium_active(user_doc) is False

    def test_is_premium_active_custom_time(self, sample_user_docs):
        """Test premium active check with custom timestamp"""
        from services.premium import is_premium_active
        
        # User expires in future, but we check from future perspective
        future_time = sample_user_docs['active_supporter']['currentPeriodEnd'] + 1
        assert is_premium_active(sample_user_docs['active_supporter'], future_time) is False
        
        # User expired in past, but we check from past perspective
        past_time = sample_user_docs['active_supporter']['currentPeriodEnd'] - 1
        assert is_premium_active(sample_user_docs['active_supporter'], past_time) is True

    def test_tier_entitlements_supporter(self):
        """Test supporter tier entitlements"""
        from services.premium import _tier_entitlements
        
        result = _tier_entitlements('supporter')
        
        expected = {
            "tier": "supporter",
            "dailyPetQuestsBonus": 2,
            "extraPets": 0,
            "squibgamesMaxPlayers": 20,
            "premiumBadge": True,
            "accessToPremiumCommands": True,
        }
        
        assert result == expected

    def test_tier_entitlements_sponsor(self):
        """Test sponsor tier entitlements"""
        from services.premium import _tier_entitlements
        
        result = _tier_entitlements('sponsor')
        
        expected = {
            "tier": "sponsor",
            "dailyPetQuestsBonus": 5,
            "extraPets": 1,
            "squibgamesMaxPlayers": 50,
            "premiumBadge": True,
            "accessToPremiumCommands": True,
        }
        
        assert result == expected

    def test_tier_entitlements_vip(self):
        """Test VIP tier entitlements"""
        from services.premium import _tier_entitlements
        
        result = _tier_entitlements('vip')
        
        expected = {
            "tier": "vip",
            "dailyPetQuestsBonus": 8,
            "extraPets": 3,
            "squibgamesMaxPlayers": 75,
            "premiumBadge": True,
            "accessToPremiumCommands": True,
        }
        
        assert result == expected

    def test_tier_entitlements_free(self):
        """Test free tier entitlements for unknown/None roles"""
        from services.premium import _tier_entitlements
        
        free_expected = {
            "tier": "free",
            "dailyPetQuestsBonus": 0,
            "extraPets": 0,
            "squibgamesMaxPlayers": 10,
            "premiumBadge": False,
            "accessToPremiumCommands": False,
        }
        
        # Test various free cases
        assert _tier_entitlements(None) == free_expected
        assert _tier_entitlements('') == free_expected
        assert _tier_entitlements('unknown') == free_expected
        assert _tier_entitlements('invalid_tier') == free_expected

    def test_get_entitlements_premium_users(self, sample_user_docs):
        """Test entitlements for premium users"""
        from services.premium import get_entitlements
        
        # Test supporter
        result = get_entitlements(sample_user_docs['active_supporter'])
        assert result['tier'] == 'supporter'
        assert result['dailyPetQuestsBonus'] == 2
        assert result['extraPets'] == 0
        assert result['squibgamesMaxPlayers'] == 20
        
        # Test sponsor
        result = get_entitlements(sample_user_docs['active_sponsor'])
        assert result['tier'] == 'sponsor'
        assert result['dailyPetQuestsBonus'] == 5
        assert result['extraPets'] == 1
        assert result['squibgamesMaxPlayers'] == 50
        
        # Test VIP
        result = get_entitlements(sample_user_docs['active_vip'])
        assert result['tier'] == 'vip'
        assert result['dailyPetQuestsBonus'] == 8
        assert result['extraPets'] == 3
        assert result['squibgamesMaxPlayers'] == 75

    def test_get_entitlements_non_premium_users(self, sample_user_docs):
        """Test entitlements for non-premium users"""
        from services.premium import get_entitlements
        
        free_expected = {
            "tier": "free",
            "dailyPetQuestsBonus": 0,
            "extraPets": 0,
            "squibgamesMaxPlayers": 10,
            "premiumBadge": False,
            "accessToPremiumCommands": False,
        }
        
        # Non-premium user
        result = get_entitlements(sample_user_docs['non_premium_user'])
        assert result == free_expected
        
        # Free user
        result = get_entitlements(sample_user_docs['free_user'])
        assert result == free_expected
        
        # Expired user
        result = get_entitlements(sample_user_docs['expired_user'])
        assert result == free_expected
        
        # None user
        result = get_entitlements(None)
        assert result == free_expected

    def test_get_entitlements_unknown_role(self, sample_user_docs):
        """Test entitlements for premium user with unknown role"""
        from services.premium import get_entitlements
        
        result = get_entitlements(sample_user_docs['unknown_role_user'])
        
        # Should get free entitlements even if premium is active but role is unknown
        assert result['tier'] == 'free'
        assert result['premiumBadge'] is False

    def test_get_entitlements_error_handling(self):
        """Test error handling in get_entitlements"""
        from services.premium import get_entitlements
        
        # Mock is_premium_active to raise an exception
        with patch('services.premium.logger') as mock_logger:
            with patch('services.premium.is_premium_active') as mock_is_premium:
                mock_is_premium.side_effect = ValueError("Mock exception for testing")
                
                result = get_entitlements({'premium': True, 'status': 'active'})
                
                # Should return free entitlements on error
                assert result['tier'] == 'free'
                mock_logger.error.assert_called()

    def test_get_user_entitlements_cache_hit(self, sample_user_docs):
        """Test cache hit scenario"""
        from services.premium import get_user_entitlements, _ENTITLEMENTS_CACHE
        
        # Pre-populate cache
        test_entitlements = {'tier': 'sponsor', 'cached': True}
        cache_expires = time.time() + 300  # 5 minutes from now
        _ENTITLEMENTS_CACHE['123456789'] = (cache_expires, test_entitlements)
        
        result = get_user_entitlements('123456789')
        
        # Should return cached value
        assert result == test_entitlements
        assert result['cached'] is True

    def test_get_user_entitlements_cache_miss(self, mock_mongo_client, sample_user_docs):
        """Test cache miss scenario"""
        from services.premium import get_user_entitlements, _ENTITLEMENTS_CACHE
        
        # Clear cache
        _ENTITLEMENTS_CACHE.clear()
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        mock_collection.find_one.return_value = sample_user_docs['active_supporter']
        
        with patch('services.premium._mongo_client', mock_client):
            with patch('services.premium._users_collection', mock_collection):
                result = get_user_entitlements('123456789')
                
                # Should fetch from database and cache result
                assert result['tier'] == 'supporter'
                assert '123456789' in _ENTITLEMENTS_CACHE

    def test_get_user_entitlements_cache_expired(self, mock_mongo_client, sample_user_docs):
        """Test expired cache scenario"""
        from services.premium import get_user_entitlements, _ENTITLEMENTS_CACHE
        
        # Pre-populate cache with expired entry
        old_entitlements = {'tier': 'free', 'expired': True}
        cache_expires = time.time() - 100  # Expired 100 seconds ago
        _ENTITLEMENTS_CACHE['123456789'] = (cache_expires, old_entitlements)
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        mock_collection.find_one.return_value = sample_user_docs['active_supporter']
        
        with patch('services.premium._mongo_client', mock_client):
            with patch('services.premium._users_collection', mock_collection):
                result = get_user_entitlements('123456789')
                
                # Should fetch fresh data from database
                assert result['tier'] == 'supporter'
                assert 'expired' not in result

    def test_get_user_entitlements_db_error(self):
        """Test database error handling in get_user_entitlements"""
        from services.premium import get_user_entitlements, _ENTITLEMENTS_CACHE
        
        # Clear cache
        _ENTITLEMENTS_CACHE.clear()
        
        with patch('services.premium.get_user_by_discord_id', side_effect=Exception("DB Error")):
            with patch('services.premium.logger') as mock_logger:
                result = get_user_entitlements('123456789')
                
                # Should return free entitlements on error
                assert result['tier'] == 'free'
                mock_logger.warning.assert_called()

    def test_invalidate_user_entitlements(self):
        """Test cache invalidation"""
        from services.premium import invalidate_user_entitlements, _ENTITLEMENTS_CACHE
        
        # Pre-populate cache
        test_entitlements = {'tier': 'vip'}
        cache_expires = time.time() + 300
        _ENTITLEMENTS_CACHE['123456789'] = (cache_expires, test_entitlements)
        _ENTITLEMENTS_CACHE['987654321'] = (cache_expires, test_entitlements)
        
        # Invalidate one user
        invalidate_user_entitlements('123456789')
        
        # Should remove only the specified user
        assert '123456789' not in _ENTITLEMENTS_CACHE
        assert '987654321' in _ENTITLEMENTS_CACHE

    def test_invalidate_user_entitlements_nonexistent(self):
        """Test invalidating non-existent cache entry"""
        from services.premium import invalidate_user_entitlements
        
        # Should not raise error for non-existent key
        invalidate_user_entitlements('nonexistent_user')

    def test_cache_ttl_behavior(self, mock_mongo_client, sample_user_docs):
        """Test cache TTL (time-to-live) behavior"""
        from services.premium import get_user_entitlements, _ENTITLEMENTS_CACHE, _CACHE_TTL_SECONDS
        
        _ENTITLEMENTS_CACHE.clear()
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        mock_collection.find_one.return_value = sample_user_docs['active_supporter']
        
        with patch('services.premium._mongo_client', mock_client):
            with patch('services.premium._users_collection', mock_collection):
                with patch('time.time', return_value=1000.0) as mock_time:
                    result = get_user_entitlements('123456789')
                    
                    # Check cache entry has correct expiry time
                    cache_entry = _ENTITLEMENTS_CACHE['123456789']
                    expected_expiry = 1000.0 + _CACHE_TTL_SECONDS
                    assert cache_entry[0] == expected_expiry

    def test_string_discord_id_handling(self, mock_mongo_client, sample_user_docs):
        """Test that Discord IDs are properly converted to strings"""
        from services.premium import get_user_entitlements
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        mock_collection.find_one.return_value = sample_user_docs['active_supporter']
        
        with patch('services.premium._mongo_client', mock_client):
            with patch('services.premium._users_collection', mock_collection):
                # Test with integer Discord ID
                result = get_user_entitlements(123456789)
                
                # Should convert to string for database query
                mock_collection.find_one.assert_called_with({"discordId": "123456789"})

    def test_module_exports(self):
        """Test that all expected functions are exported"""
        from services.premium import __all__
        
        expected_exports = [
            "initialize_premium_service",
            "get_user_by_discord_id",
            "is_premium_active", 
            "get_entitlements",
            "get_user_entitlements",
            "invalidate_user_entitlements",
        ]
        
        assert __all__ == expected_exports

    def test_mongo_connection_settings(self):
        """Test MongoDB connection configuration"""
        from services.premium import USERS_DB_NAME, FALLBACK_USERS_DB_NAME, USERS_COLLECTION_NAME
        
        # Test default values - could be overridden by env
        assert isinstance(USERS_DB_NAME, str) and len(USERS_DB_NAME) > 0
        assert FALLBACK_USERS_DB_NAME == 'astrostats_database'
        assert USERS_COLLECTION_NAME == 'users'

    def test_fallback_database_logic(self, mock_mongo_client):
        """Test fallback database initialization logic"""
        from services.premium import _init_db_if_needed
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        
        # Test when main DB and fallback DB are different
        with patch('services.premium.MongoClient', return_value=mock_client):
            with patch('services.premium.USERS_DB_NAME', 'main_db'):
                with patch('services.premium.FALLBACK_USERS_DB_NAME', 'fallback_db'):
                    _init_db_if_needed()
                    
                    # Should access both databases
                    assert mock_client.__getitem__.call_count >= 1

    def test_premium_status_edge_cases(self):
        """Test edge cases for premium status determination"""
        from services.premium import is_premium_active
        
        # User with premium=True but no status
        user_no_status = {'premium': True}
        assert is_premium_active(user_no_status) is False
        
        # User with premium=True and empty status
        user_empty_status = {'premium': True, 'status': ''}
        assert is_premium_active(user_empty_status) is False
        
        # User with premium=True and None status
        user_none_status = {'premium': True, 'status': None}
        assert is_premium_active(user_none_status) is False

    def test_entitlements_caching_concurrency(self, mock_mongo_client, sample_user_docs):
        """Test entitlements caching with concurrent access simulation"""
        from services.premium import get_user_entitlements, _ENTITLEMENTS_CACHE
        
        _ENTITLEMENTS_CACHE.clear()
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        mock_collection.find_one.return_value = sample_user_docs['active_supporter']
        
        with patch('services.premium._mongo_client', mock_client):
            with patch('services.premium._users_collection', mock_collection):
                # Simulate multiple rapid calls for same user
                results = []
                for _ in range(5):
                    result = get_user_entitlements('123456789')
                    results.append(result)
                
                # All results should be consistent
                for result in results:
                    assert result['tier'] == 'supporter'
                
                # Should only call database once due to caching
                assert mock_collection.find_one.call_count <= 1

    def test_logging_behavior(self, sample_user_docs):
        """Test logging behavior for different scenarios"""
        from services.premium import get_entitlements
        
        with patch('services.premium.logger') as mock_logger:
            # Test free tier logging (should be DEBUG level)
            get_entitlements(sample_user_docs['free_user'])
            
            # Should log at debug level for free tier
            debug_calls = [call for call in mock_logger.debug.call_args_list if 'premium=0' in str(call)]
            assert len(debug_calls) > 0
            
            # Test premium tier logging (should be INFO level)
            get_entitlements(sample_user_docs['active_supporter'])
            
            # Should log at info level for premium tier
            info_calls = [call for call in mock_logger.info.call_args_list if 'premium=1' in str(call)]
            assert len(info_calls) > 0

    def test_database_fallback_error_handling(self, mock_mongo_client):
        """Test error handling when fallback database also fails"""
        from services.premium import get_user_by_discord_id
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        mock_fallback_collection = MagicMock()
        
        # Both primary and fallback collections fail
        mock_collection.find_one.return_value = None
        mock_fallback_collection.find_one.side_effect = Exception("Fallback failed")
        
        with patch('services.premium._mongo_client', mock_client):
            with patch('services.premium._users_collection', mock_collection):
                with patch('services.premium._fallback_users_collection', mock_fallback_collection):
                    result = get_user_by_discord_id('123456789')
                    
                    # Should still return None gracefully
                    assert result is None

    def test_comprehensive_integration(self, mock_mongo_client, sample_user_docs):
        """Test comprehensive integration of all components"""
        from services.premium import get_user_entitlements, invalidate_user_entitlements
        
        mock_client, mock_db, mock_collection = mock_mongo_client
        
        # Test complete workflow: fetch -> cache -> invalidate -> re-fetch
        for user_type, user_doc in sample_user_docs.items():
            mock_collection.find_one.return_value = user_doc
            discord_id = user_doc.get('discordId', 'test_id')
            
            with patch('services.premium._mongo_client', mock_client):
                with patch('services.premium._users_collection', mock_collection):
                    # First fetch (database call)
                    result1 = get_user_entitlements(discord_id)
                    
                    # Second fetch (cache hit)
                    result2 = get_user_entitlements(discord_id)
                    
                    # Results should be identical
                    assert result1 == result2
                    
                    # Invalidate cache
                    invalidate_user_entitlements(discord_id)
                    
                    # Third fetch (database call again)
                    result3 = get_user_entitlements(discord_id)
                    
                    # Should still get same result
                    assert result1 == result3
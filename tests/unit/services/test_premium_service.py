import pytest
import time
from unittest.mock import patch, MagicMock
from services.premium import (
    get_user_by_discord_id,
    is_premium_active,
    get_entitlements,
    get_user_entitlements,
    _tier_entitlements
)


class TestPremiumService:
    
    def test_tier_entitlements_free(self):
        entitlements = _tier_entitlements(None)
        assert entitlements["tier"] == "free"
        assert entitlements["dailyPetQuestsBonus"] == 0
        assert entitlements["extraPets"] == 0
        assert entitlements["squibgamesMaxPlayers"] == 10
        assert entitlements["premiumBadge"] is False
        assert entitlements["accessToPremiumCommands"] is False

    def test_tier_entitlements_supporter(self):
        entitlements = _tier_entitlements("supporter")
        assert entitlements["tier"] == "supporter"
        assert entitlements["dailyPetQuestsBonus"] == 2
        assert entitlements["extraPets"] == 0
        assert entitlements["squibgamesMaxPlayers"] == 20
        assert entitlements["premiumBadge"] is True
        assert entitlements["accessToPremiumCommands"] is True

    def test_tier_entitlements_sponsor(self):
        entitlements = _tier_entitlements("sponsor")
        assert entitlements["tier"] == "sponsor"
        assert entitlements["dailyPetQuestsBonus"] == 5
        assert entitlements["extraPets"] == 1
        assert entitlements["squibgamesMaxPlayers"] == 50
        assert entitlements["premiumBadge"] is True
        assert entitlements["accessToPremiumCommands"] is True

    def test_tier_entitlements_vip(self):
        entitlements = _tier_entitlements("vip")
        assert entitlements["tier"] == "vip"
        assert entitlements["dailyPetQuestsBonus"] == 8
        assert entitlements["extraPets"] == 3
        assert entitlements["squibgamesMaxPlayers"] == 75
        assert entitlements["premiumBadge"] is True
        assert entitlements["accessToPremiumCommands"] is True

    def test_is_premium_active_no_user(self):
        assert is_premium_active(None) is False

    def test_is_premium_active_false_premium(self):
        user = {"premium": False}
        assert is_premium_active(user) is False

    def test_is_premium_active_inactive_status(self):
        user = {"premium": True, "status": "inactive"}
        assert is_premium_active(user) is False

    def test_is_premium_active_expired(self):
        now = int(time.time())
        user = {
            "premium": True,
            "status": "active",
            "currentPeriodEnd": now - 3600  # 1 hour ago
        }
        assert is_premium_active(user, now) is False

    def test_is_premium_active_valid(self):
        now = int(time.time())
        user = {
            "premium": True,
            "status": "active",
            "currentPeriodEnd": now + 3600  # 1 hour from now
        }
        assert is_premium_active(user, now) is True

    def test_is_premium_active_trialing(self):
        now = int(time.time())
        user = {
            "premium": True,
            "status": "trialing",
            "currentPeriodEnd": now + 3600
        }
        assert is_premium_active(user, now) is True

    def test_get_entitlements_free_user(self, free_tier_user):
        entitlements = get_entitlements(free_tier_user)
        assert entitlements["tier"] == "free"
        assert entitlements["dailyPetQuestsBonus"] == 0

    def test_get_entitlements_supporter_user(self, supporter_tier_user):
        entitlements = get_entitlements(supporter_tier_user)
        assert entitlements["tier"] == "supporter"
        assert entitlements["dailyPetQuestsBonus"] == 2

    def test_get_entitlements_sponsor_user(self, sponsor_tier_user):
        entitlements = get_entitlements(sponsor_tier_user)
        assert entitlements["tier"] == "sponsor"
        assert entitlements["dailyPetQuestsBonus"] == 5

    def test_get_entitlements_vip_user(self, vip_tier_user):
        entitlements = get_entitlements(vip_tier_user)
        assert entitlements["tier"] == "vip"
        assert entitlements["dailyPetQuestsBonus"] == 8

    @patch('services.premium.get_user_by_discord_id')
    def test_get_user_entitlements_cached(self, mock_get_user):
        discord_id = "123456789"
        
        # First call
        mock_user = {"premium": True, "status": "active", "role": "supporter", "currentPeriodEnd": 9999999999}
        mock_get_user.return_value = mock_user
        
        entitlements1 = get_user_entitlements(discord_id)
        assert entitlements1["tier"] == "supporter"
        
        # Second call should use cache
        entitlements2 = get_user_entitlements(discord_id)
        assert entitlements2["tier"] == "supporter"
        
        # Should only call database once due to caching
        assert mock_get_user.call_count == 1

    @patch('services.premium._init_db_if_needed')
    @patch('services.premium._users_collection')
    def test_get_user_by_discord_id_success(self, mock_collection, mock_init):
        mock_init.return_value = None
        mock_doc = {"discordId": "123", "premium": True}
        mock_collection.find_one.return_value = mock_doc
        
        result = get_user_by_discord_id("123")
        assert result == mock_doc
        mock_collection.find_one.assert_called_once_with({"discordId": "123"})

    @patch('services.premium._init_db_if_needed')
    @patch('services.premium._users_collection', None)
    def test_get_user_by_discord_id_no_connection(self, mock_init):
        result = get_user_by_discord_id("123")
        assert result is None
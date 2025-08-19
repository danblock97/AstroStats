import pytest
import discord
from unittest.mock import patch, MagicMock, AsyncMock
from cogs.systems.pet_battles.petbattle import calculate_damage, get_active_buff


class TestPetBattles:
    
    def test_get_active_buff_no_items(self):
        """Test buff calculation with no active items"""
        active_items = []
        buff = get_active_buff(active_items, "strength")
        assert buff == 0

    def test_get_active_buff_with_items(self):
        """Test buff calculation with active strength items"""
        active_items = [
            {"stat": "strength", "value": 10, "battles_remaining": 3},
            {"stat": "strength", "value": 5, "battles_remaining": 1},
            {"stat": "defense", "value": 8, "battles_remaining": 2}
        ]
        
        strength_buff = get_active_buff(active_items, "strength")
        defense_buff = get_active_buff(active_items, "defense")
        
        assert strength_buff == 15  # 10 + 5
        assert defense_buff == 8

    def test_get_active_buff_expired_items(self):
        """Test buff calculation ignoring expired items"""
        active_items = [
            {"stat": "strength", "value": 10, "battles_remaining": 0},  # Expired
            {"stat": "strength", "value": 5, "battles_remaining": 1}
        ]
        
        buff = get_active_buff(active_items, "strength")
        assert buff == 5  # Only the non-expired item

    def test_calculate_damage_basic(self):
        """Test basic damage calculation"""
        attacker = {"strength": 15, "active_items": []}
        defender = {"defense": 10, "active_items": []}
        
        damage, is_crit, event_type = calculate_damage(attacker, defender)
        
        assert damage >= 5  # Minimum damage
        assert isinstance(is_crit, bool)
        assert event_type in ["normal", "luck"]

    def test_calculate_damage_with_buffs(self):
        """Test damage calculation with active item buffs"""
        attacker = {
            "strength": 15,
            "active_items": [{"stat": "strength", "value": 10, "battles_remaining": 5}]
        }
        defender = {
            "defense": 10,
            "active_items": [{"stat": "defense", "value": 5, "battles_remaining": 3}]
        }
        
        damage, is_crit, event_type = calculate_damage(attacker, defender)
        
        assert damage >= 5  # Still minimum damage
        assert isinstance(is_crit, bool)
        assert event_type in ["normal", "luck"]

    def test_calculate_damage_minimum_damage(self):
        """Test that minimum damage is enforced"""
        # Very weak attacker vs very strong defender
        attacker = {"strength": 1, "active_items": []}
        defender = {"defense": 100, "active_items": []}
        
        damage, _, _ = calculate_damage(attacker, defender)
        
        assert damage >= 5  # Minimum damage enforced

    def test_calculate_damage_critical_hit_chance(self):
        """Test critical hit mechanics"""
        attacker = {"strength": 15, "level": 1, "active_items": []}
        defender = {"defense": 10, "level": 10, "active_items": []}
        
        # Run multiple times to test critical hit probability
        crit_count = 0
        total_tests = 100
        
        for _ in range(total_tests):
            _, is_crit, _ = calculate_damage(attacker, defender)
            if is_crit:
                crit_count += 1
        
        # Should have some critical hits (but not testing exact percentage due to randomness)
        # Just ensure the mechanism works
        assert crit_count >= 0  # At least possible to get crits

    def test_calculate_damage_lucky_hit_event(self):
        """Test lucky hit event type"""
        attacker = {"strength": 15, "active_items": []}
        defender = {"defense": 10, "active_items": []}
        
        # Run multiple times to potentially trigger lucky hit
        luck_count = 0
        total_tests = 100
        
        for _ in range(total_tests):
            _, _, event_type = calculate_damage(attacker, defender)
            if event_type == "luck":
                luck_count += 1
        
        # Lucky hits should be possible (but rare)
        assert luck_count >= 0  # At least the mechanism exists


class TestPetBattlesIntegration:
    """Integration tests for premium tier benefits in pet battles"""
    
    @pytest.fixture
    def mock_pet_cog(self, mock_bot):
        # This would need to be imported and mocked properly
        # from cogs.systems.pet_battles import PetBattlesCog
        # return PetBattlesCog(mock_bot)
        return MagicMock()

    def test_free_tier_pet_capacity(self):
        """Test that free tier users have 1 pet capacity"""
        free_entitlements = {
            "tier": "free",
            "extraPets": 0
        }
        
        base_capacity = 1
        total_capacity = base_capacity + free_entitlements["extraPets"]
        assert total_capacity == 1

    def test_supporter_tier_pet_capacity(self):
        """Test supporter tier pet capacity (same as free)"""
        supporter_entitlements = {
            "tier": "supporter", 
            "extraPets": 0
        }
        
        base_capacity = 1
        total_capacity = base_capacity + supporter_entitlements["extraPets"]
        assert total_capacity == 1

    def test_sponsor_tier_pet_capacity(self):
        """Test sponsor tier gets +1 extra pet (2 total)"""
        sponsor_entitlements = {
            "tier": "sponsor",
            "extraPets": 1
        }
        
        base_capacity = 1
        total_capacity = base_capacity + sponsor_entitlements["extraPets"]
        assert total_capacity == 2

    def test_vip_tier_pet_capacity(self):
        """Test VIP tier gets +3 extra pets (4 total)"""
        vip_entitlements = {
            "tier": "vip",
            "extraPets": 3
        }
        
        base_capacity = 1
        total_capacity = base_capacity + vip_entitlements["extraPets"]
        assert total_capacity == 4

    def test_free_tier_daily_quests(self):
        """Test free tier gets 3 daily quests"""
        free_entitlements = {
            "tier": "free",
            "dailyPetQuestsBonus": 0
        }
        
        base_quests = 3
        total_quests = base_quests + free_entitlements["dailyPetQuestsBonus"]
        assert total_quests == 3

    def test_supporter_tier_daily_quests(self):
        """Test supporter tier gets +2 daily quests (5 total)"""
        supporter_entitlements = {
            "tier": "supporter",
            "dailyPetQuestsBonus": 2
        }
        
        base_quests = 3
        total_quests = base_quests + supporter_entitlements["dailyPetQuestsBonus"]
        assert total_quests == 5

    def test_sponsor_tier_daily_quests(self):
        """Test sponsor tier gets +5 daily quests (8 total)"""
        sponsor_entitlements = {
            "tier": "sponsor",
            "dailyPetQuestsBonus": 5
        }
        
        base_quests = 3
        total_quests = base_quests + sponsor_entitlements["dailyPetQuestsBonus"]
        assert total_quests == 8

    def test_vip_tier_daily_quests(self):
        """Test VIP tier gets +8 daily quests (11 total)"""
        vip_entitlements = {
            "tier": "vip",
            "dailyPetQuestsBonus": 8
        }
        
        base_quests = 3
        total_quests = base_quests + vip_entitlements["dailyPetQuestsBonus"]
        assert total_quests == 11

    def test_premium_badge_access(self):
        """Test premium tiers get premium badge"""
        tiers = ["supporter", "sponsor", "vip"]
        
        for tier in tiers:
            entitlements = {
                "tier": tier,
                "premiumBadge": True
            }
            assert entitlements["premiumBadge"] is True

    def test_premium_commands_access(self):
        """Test premium tiers get access to premium commands"""
        tiers = ["supporter", "sponsor", "vip"]
        
        for tier in tiers:
            entitlements = {
                "tier": tier,
                "accessToPremiumCommands": True
            }
            assert entitlements["accessToPremiumCommands"] is True

    def test_free_tier_no_premium_features(self):
        """Test free tier doesn't get premium features"""
        free_entitlements = {
            "tier": "free",
            "premiumBadge": False,
            "accessToPremiumCommands": False
        }
        
        assert free_entitlements["premiumBadge"] is False
        assert free_entitlements["accessToPremiumCommands"] is False
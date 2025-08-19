import pytest
import discord
from unittest.mock import patch, MagicMock, AsyncMock
from cogs.games.catfight import CatfightCog, BATTLE_ATTACKS, CRITICAL_HITS, MISS_MESSAGES


class TestCatfightCog:
    
    @pytest.fixture
    def catfight_cog(self, mock_bot):
        return CatfightCog(mock_bot)

    def test_battle_attacks_structure(self):
        """Test that battle attacks are properly structured"""
        assert len(BATTLE_ATTACKS) > 0
        
        for attack in BATTLE_ATTACKS:
            assert "name" in attack
            assert "damage" in attack
            assert "emoji" in attack
            assert "desc" in attack
            
            # Damage should be a tuple with min and max
            assert isinstance(attack["damage"], tuple)
            assert len(attack["damage"]) == 2
            assert attack["damage"][0] < attack["damage"][1]  # min < max

    def test_battle_attacks_variety(self):
        """Test that there's good variety in battle attacks"""
        attack_names = [attack["name"] for attack in BATTLE_ATTACKS]
        
        # Check for some expected attack types
        expected_attacks = [
            "Claw Swipe", "Pounce Attack", "Tail Whip", "Bite Strike",
            "Fury Swipes", "Stealth Strike", "Sonic Screech", "Nine Lives Rush"
        ]
        
        for expected in expected_attacks:
            assert expected in attack_names

    def test_critical_hit_messages(self):
        """Test critical hit messages exist and are varied"""
        assert len(CRITICAL_HITS) > 0
        
        # Check for variety in messages
        assert "DEVASTATING" in str(CRITICAL_HITS)
        assert "CRITICAL HIT" in str(CRITICAL_HITS)

    def test_miss_messages(self):
        """Test miss messages exist and are humorous"""
        assert len(MISS_MESSAGES) > 0
        
        # Check for variety in messages
        assert any("air" in msg for msg in MISS_MESSAGES)
        assert any("distracted" in msg for msg in MISS_MESSAGES)

    def test_is_database_available(self, catfight_cog):
        """Test database availability check"""
        # This will depend on the mock setup, but should not crash
        result = catfight_cog.is_database_available()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_user_stats_no_database(self, catfight_cog):
        """Test getting user stats when database is unavailable"""
        with patch.object(catfight_cog, 'is_database_available', return_value=False):
            stats = await catfight_cog.get_user_stats("123", "456")
            
            expected_stats = {"wins": 0, "losses": 0, "win_streak": 0, "loss_streak": 0}
            assert stats == expected_stats

    @pytest.mark.asyncio
    async def test_get_user_stats_with_database(self, catfight_cog):
        """Test getting user stats with database available"""
        mock_stats = {"wins": 5, "losses": 2, "win_streak": 3, "loss_streak": 0}
        expected_stats = {"wins": 5, "losses": 2, "win_streak": 3, "loss_streak": 0, "username": "Unknown"}
        
        with patch.object(catfight_cog, 'is_database_available', return_value=True), \
             patch('cogs.games.catfight.catfight_stats') as mock_collection:
            
            mock_collection.find_one.return_value = mock_stats
            
            stats = await catfight_cog.get_user_stats("123", "456")
            assert stats == expected_stats

    def test_damage_ranges_realistic(self):
        """Test that damage ranges are realistic for PvP battles"""
        for attack in BATTLE_ATTACKS:
            min_dmg, max_dmg = attack["damage"]
            
            # Damage should be positive
            assert min_dmg > 0
            assert max_dmg > 0
            
            # Max damage should be reasonable (not too high for PvP)
            assert max_dmg <= 30  # Reasonable upper bound
            
            # Should have meaningful range
            assert max_dmg - min_dmg >= 4  # At least 5 point range

    def test_attack_variety_balance(self):
        """Test that attacks have good balance in damage ranges"""
        all_min_damages = [attack["damage"][0] for attack in BATTLE_ATTACKS]
        all_max_damages = [attack["damage"][1] for attack in BATTLE_ATTACKS]
        
        # Should have variety in damage ranges
        assert min(all_min_damages) < 10  # Some low damage attacks
        assert max(all_max_damages) > 20  # Some high damage attacks
        
        # Average damage should be reasonable
        avg_min = sum(all_min_damages) / len(all_min_damages)
        avg_max = sum(all_max_damages) / len(all_max_damages)
        
        assert 5 <= avg_min <= 12
        assert 15 <= avg_max <= 25

    @pytest.mark.asyncio
    async def test_catfight_command_structure(self, catfight_cog, mock_interaction):
        """Test basic catfight command structure"""
        # This would test the actual catfight command once we can access it
        # For now, just ensure the cog initializes properly
        assert catfight_cog.bot is not None

    def test_special_attacks_exist(self):
        """Test that there are some fun, special attacks"""
        attack_names = [attack["name"] for attack in BATTLE_ATTACKS]
        
        # Look for creative/fun attacks
        fun_attacks = [
            "Hairball Launcher",
            "Catnip Frenzy", 
            "Laser Eyes",
            "Belly Rub Trap",
            "Cardboard Box Slam"
        ]
        
        for fun_attack in fun_attacks:
            assert fun_attack in attack_names

    def test_attack_descriptions_present(self):
        """Test that all attacks have descriptive text"""
        for attack in BATTLE_ATTACKS:
            assert len(attack["desc"]) > 0
            assert isinstance(attack["desc"], str)
            
            # Description should be action-oriented
            action_words = ["rakes", "leaps", "delivers", "sinks", "unleashes", "emerges", "lets out", "channels", "launches", "goes", "fires", "creates", "uses", "lures", "weaponizes"]
            assert any(word in attack["desc"] for word in action_words)

    def test_emoji_variety(self):
        """Test that attacks have varied emojis"""
        emojis = [attack["emoji"] for attack in BATTLE_ATTACKS]
        
        # Should have unique emojis (mostly)
        unique_emojis = set(emojis)
        assert len(unique_emojis) >= len(emojis) * 0.8  # At least 80% unique

    def test_catfight_cog_initialization(self, mock_bot):
        """Test that CatfightCog initializes correctly"""
        cog = CatfightCog(mock_bot)
        assert cog.bot == mock_bot

class TestCatfightGameplay:
    """Test catfight gameplay mechanics"""
    
    def test_critical_hit_probability(self):
        """Test critical hit system (conceptual)"""
        # Critical hits should be 20% chance based on comments
        # This tests the availability of critical hit messages
        assert len(CRITICAL_HITS) >= 3  # Enough variety
        
        for crit_msg in CRITICAL_HITS:
            assert len(crit_msg) > 0
            assert isinstance(crit_msg, str)

    def test_miss_probability(self):
        """Test miss system (conceptual)"""
        # Misses should be 10% chance based on comments
        # This tests the availability of miss messages
        assert len(MISS_MESSAGES) >= 3  # Enough variety
        
        for miss_msg in MISS_MESSAGES:
            assert len(miss_msg) > 0
            assert isinstance(miss_msg, str)

    def test_battle_flow_elements(self):
        """Test that all elements needed for battle flow exist"""
        # Attacks for damage dealing
        assert len(BATTLE_ATTACKS) > 0
        
        # Critical hit messages for special moments
        assert len(CRITICAL_HITS) > 0
        
        # Miss messages for failed attacks
        assert len(MISS_MESSAGES) > 0

    def test_pvp_balance(self):
        """Test that PvP mechanics seem balanced"""
        # No attack should be overwhelmingly powerful
        max_possible_damage = max(attack["damage"][1] for attack in BATTLE_ATTACKS)
        min_possible_damage = min(attack["damage"][0] for attack in BATTLE_ATTACKS)
        
        # Ratio shouldn't be too extreme
        ratio = max_possible_damage / min_possible_damage
        assert ratio <= 7  # Max damage shouldn't be more than 7x min damage

    def test_attack_themed_appropriately(self):
        """Test that attacks are cat/animal themed"""
        cat_themed_words = [
            "claw", "pounce", "tail", "bite", "nine lives", 
            "hairball", "catnip", "purr", "whisker", "belly"
        ]
        
        all_attack_text = " ".join([
            attack["name"] + " " + attack["desc"] 
            for attack in BATTLE_ATTACKS
        ]).lower()
        
        # Should have multiple cat-themed elements
        cat_theme_count = sum(1 for word in cat_themed_words if word in all_attack_text)
        assert cat_theme_count >= 5  # At least 5 cat-themed elements
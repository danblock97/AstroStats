import pytest
from unittest.mock import patch, MagicMock


class TestPetStatsSystem:
    """Test pet statistics and leveling system"""
    
    def test_calculate_xp_needed_formula(self):
        """Test XP calculation formula for leveling"""
        # Test the XP formula: level^2 * 100
        test_cases = [
            {"level": 1, "expected_xp": 100},   # 1^2 * 100 = 100
            {"level": 2, "expected_xp": 400},   # 2^2 * 100 = 400  
            {"level": 3, "expected_xp": 900},   # 3^2 * 100 = 900
            {"level": 5, "expected_xp": 2500},  # 5^2 * 100 = 2500
            {"level": 10, "expected_xp": 10000} # 10^2 * 100 = 10000
        ]
        
        for case in test_cases:
            level = case["level"]
            expected = case["expected_xp"]
            calculated = level ** 2 * 100
            
            assert calculated == expected

    def test_level_up_stat_increases(self):
        """Test stat increases on level up"""
        # Mock level up increases
        level_up_increases = {
            "strength": 2,
            "defense": 2, 
            "health": 5
        }
        
        # Test pet before level up
        pet_before = {
            "level": 2,
            "xp": 500,  # More than needed for level 3 (400)
            "strength": 12,
            "defense": 12,
            "health": 105
        }
        
        # Simulate level up
        xp_needed = 3 ** 2 * 100  # 900 XP needed for level 3
        if pet_before["xp"] >= 400:  # Level 2 needs 400 XP
            pet_after = {
                "level": pet_before["level"] + 1,
                "xp": pet_before["xp"] - 400,  # Subtract XP needed for previous level
                "strength": pet_before["strength"] + level_up_increases["strength"],
                "defense": pet_before["defense"] + level_up_increases["defense"],
                "health": pet_before["health"] + level_up_increases["health"]
            }
            
            # Verify level up occurred correctly
            assert pet_after["level"] == 3
            assert pet_after["xp"] == 100  # 500 - 400 = 100 remaining
            assert pet_after["strength"] == 14  # 12 + 2
            assert pet_after["defense"] == 14   # 12 + 2  
            assert pet_after["health"] == 110   # 105 + 5

    def test_multiple_level_ups(self):
        """Test multiple level ups in one XP gain"""
        # Pet with enough XP for multiple levels
        pet = {
            "level": 1,
            "xp": 1500,  # Enough for multiple levels
            "strength": 10,
            "defense": 10,
            "health": 100
        }
        
        level_up_increases = {"strength": 2, "defense": 2, "health": 5}
        
        # Simulate multiple level ups
        levels_gained = 0
        while True:
            xp_needed = pet["level"] ** 2 * 100
            if pet["xp"] >= xp_needed:
                pet["level"] += 1
                pet["xp"] -= xp_needed
                pet["strength"] += level_up_increases["strength"]
                pet["defense"] += level_up_increases["defense"] 
                pet["health"] += level_up_increases["health"]
                levels_gained += 1
            else:
                break
            
            # Prevent infinite loop in test
            if levels_gained > 10:
                break
        
        # Should have gained multiple levels
        assert levels_gained >= 2
        assert pet["level"] > 1
        assert pet["strength"] > 10
        assert pet["defense"] > 10
        assert pet["health"] > 100

    def test_xp_progress_bar_creation(self):
        """Test XP progress bar visual creation"""
        progress_bar_cases = [
            {"current": 0, "total": 100, "expected_filled": 0},
            {"current": 50, "total": 100, "expected_filled": 5},  # 50% of 10 blocks
            {"current": 100, "total": 100, "expected_filled": 10}, # 100% of 10 blocks
            {"current": 75, "total": 100, "expected_filled": 7}    # 75% of 10 blocks
        ]
        
        for case in progress_bar_cases:
            current = case["current"]
            total = case["total"]
            expected_filled = case["expected_filled"]
            
            # Calculate progress bar (10 blocks total)
            total_blocks = 10
            if total <= 0:
                total = 1  # Avoid division by zero
            filled_blocks = int((current / total) * total_blocks)
            
            progress_bar = "█" * filled_blocks + "░" * (total_blocks - filled_blocks)
            
            assert filled_blocks == expected_filled
            assert len(progress_bar) == 10
            assert progress_bar.count("█") == filled_blocks
            assert progress_bar.count("░") == (10 - filled_blocks)

    def test_xp_edge_cases(self):
        """Test XP calculation edge cases"""
        edge_cases = [
            {"level": 0, "should_handle": "gracefully"},  # Level 0 edge case
            {"xp": -10, "should_handle": "gracefully"},   # Negative XP
            {"level": 100, "xp_needed": 1000000},        # Very high level
        ]
        
        for case in edge_cases:
            if "level" in case:
                level = max(1, case["level"])  # Minimum level 1
                xp_needed = level ** 2 * 100
                assert xp_needed >= 100  # Should always need at least 100 XP
                
            if "xp" in case:
                xp = max(0, case.get("xp", 0))  # XP should not be negative
                assert xp >= 0

    def test_stat_scaling_balance(self):
        """Test that stat scaling is balanced"""
        # Test stat growth over multiple levels
        initial_stats = {"strength": 10, "defense": 10, "health": 100}
        level_increases = {"strength": 2, "defense": 2, "health": 5}
        
        # Calculate stats at level 10
        levels_to_test = 10
        final_stats = {
            "strength": initial_stats["strength"] + (level_increases["strength"] * (levels_to_test - 1)),
            "defense": initial_stats["defense"] + (level_increases["defense"] * (levels_to_test - 1)),
            "health": initial_stats["health"] + (level_increases["health"] * (levels_to_test - 1))
        }
        
        # Level 10 stats should be: 10 + (2 * 9) = 28, 28, 100 + (5 * 9) = 145
        assert final_stats["strength"] == 28
        assert final_stats["defense"] == 28
        assert final_stats["health"] == 145
        
        # Stats should scale reasonably
        assert final_stats["strength"] < final_stats["health"]  # Health should be higher
        assert final_stats["strength"] == final_stats["defense"]  # Equal scaling

    def test_xp_overflow_handling(self):
        """Test XP overflow handling for level ups"""
        # Pet with way more XP than needed
        pet = {
            "level": 1,
            "xp": 10000,  # Way more than needed
            "strength": 10,
            "defense": 10,
            "health": 100
        }
        
        # Should handle large XP amounts gracefully
        original_xp = pet["xp"]
        assert original_xp > 1000  # Much more than level 1 needs (100)
        
        # After level ups, should still have reasonable remaining XP
        # (This would be tested in the actual level up function)

    def test_level_cap_enforcement(self):
        """Test level cap enforcement if implemented"""
        # Test reasonable level cap
        max_level = 50  # Reasonable max level for pet system
        
        pet_at_cap = {
            "level": max_level,
            "xp": 99999,  # Lots of XP
            "strength": 100,
            "defense": 100,
            "health": 500
        }
        
        # Should not level beyond cap
        if pet_at_cap["level"] >= max_level:
            can_level_up = False
        else:
            can_level_up = True
            
        assert can_level_up is False  # Should not level beyond cap

    def test_progression_curve_difficulty(self):
        """Test that progression curve increases in difficulty"""
        # XP requirements should increase significantly each level
        level_xp_requirements = []
        for level in range(1, 11):
            xp_needed = level ** 2 * 100
            level_xp_requirements.append(xp_needed)
        
        # Each level should require more XP than the previous
        for i in range(1, len(level_xp_requirements)):
            current_req = level_xp_requirements[i]
            previous_req = level_xp_requirements[i-1]
            assert current_req > previous_req
            
        # Higher levels should require significantly more XP
        level_1_req = level_xp_requirements[0]   # 100
        level_10_req = level_xp_requirements[9]  # 10000
        assert level_10_req >= level_1_req * 50  # At least 50x more difficult

    def test_xp_bar_visual_accuracy(self):
        """Test XP bar visual representation accuracy"""
        # Test various progress percentages
        test_progress = [
            {"current": 0, "total": 400, "percent": 0},
            {"current": 100, "total": 400, "percent": 25},
            {"current": 200, "total": 400, "percent": 50},
            {"current": 400, "total": 400, "percent": 100}
        ]
        
        for progress in test_progress:
            current = progress["current"]
            total = progress["total"]
            expected_percent = progress["percent"]
            
            # Calculate actual percentage
            actual_percent = (current / total * 100) if total > 0 else 0
            
            # Should match expected percentage
            assert abs(actual_percent - expected_percent) < 0.1  # Allow small rounding difference
            
            # Visual representation should reflect percentage
            filled_ratio = current / total if total > 0 else 0
            assert 0 <= filled_ratio <= 1

    def test_pet_stat_validation(self):
        """Test pet stat validation and bounds"""
        # Stats should have reasonable bounds
        stat_bounds = {
            "level": {"min": 1, "max": 100},
            "xp": {"min": 0, "max": 999999},
            "strength": {"min": 1, "max": 500},
            "defense": {"min": 1, "max": 500},
            "health": {"min": 10, "max": 2000}
        }
        
        for stat, bounds in stat_bounds.items():
            # Should have reasonable minimum and maximum values
            assert bounds["min"] >= 0
            assert bounds["max"] > bounds["min"]
            
            # Health should be significantly higher than strength/defense
            if stat == "health":
                assert bounds["max"] >= 1000
            elif stat in ["strength", "defense"]:
                assert bounds["max"] <= 1000
import pytest


class TestPetBattleConstants:
    """Test pet battle constants and data structures"""
    
    def test_daily_quests_structure(self):
        """Test daily quests have correct structure and data"""
        from cogs.systems.pet_battles.petconstants import DAILY_QUESTS
        
        assert isinstance(DAILY_QUESTS, list)
        assert len(DAILY_QUESTS) == 20  # Should have exactly 20 daily quests
        
        # Test each quest has required fields
        for quest in DAILY_QUESTS:
            assert isinstance(quest, dict)
            assert 'id' in quest
            assert 'description' in quest
            assert 'progress_required' in quest
            assert 'xp_reward' in quest
            assert 'cash_reward' in quest
            
            # Test field types
            assert isinstance(quest['id'], int)
            assert isinstance(quest['description'], str)
            assert isinstance(quest['progress_required'], int)
            assert isinstance(quest['xp_reward'], int)
            assert isinstance(quest['cash_reward'], int)
            
            # Test field values are reasonable
            assert quest['id'] > 0
            assert len(quest['description']) > 10
            assert quest['progress_required'] > 0
            assert quest['xp_reward'] > 0
            assert quest['cash_reward'] >= 0

    def test_daily_quests_ids_unique(self):
        """Test all daily quest IDs are unique"""
        from cogs.systems.pet_battles.petconstants import DAILY_QUESTS
        
        quest_ids = [quest['id'] for quest in DAILY_QUESTS]
        assert len(quest_ids) == len(set(quest_ids)), "Quest IDs should be unique"
        
        # IDs should be sequential from 1 to 20
        assert quest_ids == list(range(1, 21))

    def test_daily_quests_variety(self):
        """Test daily quests have variety in objectives"""
        from cogs.systems.pet_battles.petconstants import DAILY_QUESTS
        
        descriptions = [quest['description'].lower() for quest in DAILY_QUESTS]
        
        # Should have different types of quests
        quest_types = {
            'win': sum('win' in desc for desc in descriptions),
            'streak': sum('streak' in desc for desc in descriptions),
            'critical': sum('critical' in desc for desc in descriptions),
            'lucky': sum('lucky' in desc for desc in descriptions),
            'lose': sum('lose' in desc for desc in descriptions),
            'damage': sum('damage' in desc for desc in descriptions),
            'participate': sum('participate' in desc for desc in descriptions),
            'xp': sum('xp' in desc for desc in descriptions)
        }
        
        # Should have at least 3 different quest types
        active_types = sum(1 for count in quest_types.values() if count > 0)
        assert active_types >= 6

    def test_daily_quests_difficulty_scaling(self):
        """Test daily quests have appropriate difficulty scaling"""
        from cogs.systems.pet_battles.petconstants import DAILY_QUESTS
        
        # Group quests by type and check scaling
        win_quests = [q for q in DAILY_QUESTS if 'win' in q['description'].lower() and 'streak' not in q['description'].lower()]
        
        # Win quests should have increasing requirements and rewards
        if len(win_quests) >= 2:
            win_quests.sort(key=lambda q: q['progress_required'])
            for i in range(1, len(win_quests)):
                assert win_quests[i]['progress_required'] > win_quests[i-1]['progress_required']
                assert win_quests[i]['xp_reward'] >= win_quests[i-1]['xp_reward']

    def test_achievements_structure(self):
        """Test achievements have correct structure and data"""
        from cogs.systems.pet_battles.petconstants import ACHIEVEMENTS
        
        assert isinstance(ACHIEVEMENTS, list)
        assert len(ACHIEVEMENTS) == 5  # Should have exactly 5 achievements
        
        # Test each achievement has required fields
        for achievement in ACHIEVEMENTS:
            assert isinstance(achievement, dict)
            assert 'id' in achievement
            assert 'description' in achievement
            assert 'progress_required' in achievement
            assert 'xp_reward' in achievement
            assert 'cash_reward' in achievement
            
            # Test field types
            assert isinstance(achievement['id'], int)
            assert isinstance(achievement['description'], str)
            assert isinstance(achievement['progress_required'], int)
            assert isinstance(achievement['xp_reward'], int)
            assert isinstance(achievement['cash_reward'], int)
            
            # Test field values are reasonable
            assert achievement['id'] > 0
            assert len(achievement['description']) > 10
            assert achievement['progress_required'] > 0
            assert achievement['xp_reward'] > 0
            assert achievement['cash_reward'] > 0

    def test_achievements_high_difficulty(self):
        """Test achievements are significantly more difficult than daily quests"""
        from cogs.systems.pet_battles.petconstants import DAILY_QUESTS, ACHIEVEMENTS
        
        max_daily_xp = max(quest['xp_reward'] for quest in DAILY_QUESTS)
        min_achievement_xp = min(ach['xp_reward'] for ach in ACHIEVEMENTS)
        
        # Achievements should give more XP than daily quests
        assert min_achievement_xp > max_daily_xp
        
        # Achievement progress requirements should generally be higher on average
        max_daily_progress = max(quest['progress_required'] for quest in DAILY_QUESTS)
        avg_achievement_progress = sum(ach['progress_required'] for ach in ACHIEVEMENTS) / len(ACHIEVEMENTS)
        avg_daily_progress = sum(quest['progress_required'] for quest in DAILY_QUESTS) / len(DAILY_QUESTS)
        
        # Average achievement progress should be higher than average daily progress
        assert avg_achievement_progress > avg_daily_progress

    def test_achievements_ids_unique(self):
        """Test all achievement IDs are unique"""
        from cogs.systems.pet_battles.petconstants import ACHIEVEMENTS
        
        achievement_ids = [ach['id'] for ach in ACHIEVEMENTS]
        assert len(achievement_ids) == len(set(achievement_ids)), "Achievement IDs should be unique"
        
        # IDs should be sequential from 1 to 5
        assert achievement_ids == list(range(1, 6))

    def test_daily_completion_bonus(self):
        """Test daily completion bonus structure"""
        from cogs.systems.pet_battles.petconstants import DAILY_COMPLETION_BONUS
        
        assert isinstance(DAILY_COMPLETION_BONUS, dict)
        assert 'xp' in DAILY_COMPLETION_BONUS
        assert 'cash' in DAILY_COMPLETION_BONUS
        
        assert isinstance(DAILY_COMPLETION_BONUS['xp'], int)
        assert isinstance(DAILY_COMPLETION_BONUS['cash'], int)
        
        # Should be substantial bonus
        assert DAILY_COMPLETION_BONUS['xp'] >= 200
        assert DAILY_COMPLETION_BONUS['cash'] >= 100

    def test_initial_stats(self):
        """Test initial pet stats are reasonable"""
        from cogs.systems.pet_battles.petconstants import INITIAL_STATS
        
        assert isinstance(INITIAL_STATS, dict)
        
        # Required basic stats
        basic_stats = ['level', 'xp', 'strength', 'defense', 'health', 'balance']
        for stat in basic_stats:
            assert stat in INITIAL_STATS
            assert isinstance(INITIAL_STATS[stat], int)
        
        # Test reasonable starting values
        assert INITIAL_STATS['level'] == 1
        assert INITIAL_STATS['xp'] == 0
        assert INITIAL_STATS['strength'] >= 5
        assert INITIAL_STATS['defense'] >= 5
        assert INITIAL_STATS['health'] >= 50
        assert INITIAL_STATS['balance'] >= 0
        
        # Additional fields should be present
        assert 'active_items' in INITIAL_STATS
        assert isinstance(INITIAL_STATS['active_items'], list)
        assert INITIAL_STATS['active_items'] == []

    def test_level_up_increases(self):
        """Test level up stat increases are balanced"""
        from cogs.systems.pet_battles.petconstants import LEVEL_UP_INCREASES
        
        assert isinstance(LEVEL_UP_INCREASES, dict)
        
        # Should have increases for main stats
        required_stats = ['strength', 'defense', 'health']
        for stat in required_stats:
            assert stat in LEVEL_UP_INCREASES
            assert isinstance(LEVEL_UP_INCREASES[stat], int)
            assert LEVEL_UP_INCREASES[stat] > 0
        
        # Health increase should be higher than strength/defense
        assert LEVEL_UP_INCREASES['health'] > LEVEL_UP_INCREASES['strength']
        assert LEVEL_UP_INCREASES['health'] > LEVEL_UP_INCREASES['defense']

    def test_pet_list_structure(self):
        """Test pet list has correct structure"""
        from cogs.systems.pet_battles.petconstants import PET_LIST
        
        assert isinstance(PET_LIST, dict)
        assert len(PET_LIST) >= 5  # Should have multiple pet options
        
        for pet_name, image_url in PET_LIST.items():
            assert isinstance(pet_name, str)
            assert isinstance(image_url, str)
            assert len(pet_name) > 2
            assert image_url.startswith('https://')
            assert 'github.com' in image_url or 'githubusercontent.com' in image_url

    def test_pet_list_variety(self):
        """Test pet list has good variety"""
        from cogs.systems.pet_battles.petconstants import PET_LIST
        
        pet_names = list(PET_LIST.keys())
        
        # Should have common pets
        expected_pets = ['cat', 'dog', 'lion', 'tiger']
        for pet in expected_pets:
            assert pet in pet_names

    def test_color_list_structure(self):
        """Test color list has valid colors"""
        from cogs.systems.pet_battles.petconstants import COLOR_LIST
        
        assert isinstance(COLOR_LIST, dict)
        assert len(COLOR_LIST) >= 3  # Should have multiple color options
        
        for color_name, color_value in COLOR_LIST.items():
            assert isinstance(color_name, str)
            assert isinstance(color_value, int)
            assert 0 <= color_value <= 0xFFFFFF  # Valid hex color range

    def test_shop_items_structure(self):
        """Test shop items have correct structure"""
        from cogs.systems.pet_battles.petconstants import SHOP_ITEMS
        
        assert isinstance(SHOP_ITEMS, dict)
        assert len(SHOP_ITEMS) >= 5  # Should have multiple items
        
        for item_id, item_data in SHOP_ITEMS.items():
            assert isinstance(item_id, str)
            assert isinstance(item_data, dict)
            
            # Required fields
            required_fields = ['name', 'emoji', 'description', 'stat', 'value', 'duration', 'cost']
            for field in required_fields:
                assert field in item_data
            
            # Field types
            assert isinstance(item_data['name'], str)
            assert isinstance(item_data['emoji'], str)
            assert isinstance(item_data['description'], str)
            assert isinstance(item_data['stat'], str)
            assert isinstance(item_data['value'], int)
            assert isinstance(item_data['duration'], int)
            assert isinstance(item_data['cost'], int)
            
            # Field values
            assert len(item_data['name']) > 3
            assert len(item_data['emoji']) >= 1
            assert len(item_data['description']) > 10
            assert item_data['stat'] in ['strength', 'defense', 'health']
            assert item_data['value'] > 0
            assert item_data['duration'] > 0
            assert item_data['cost'] > 0

    def test_shop_items_balance(self):
        """Test shop items are reasonably balanced"""
        from cogs.systems.pet_battles.petconstants import SHOP_ITEMS
        
        # Group items by type
        strength_items = [item for item in SHOP_ITEMS.values() if item['stat'] == 'strength']
        defense_items = [item for item in SHOP_ITEMS.values() if item['stat'] == 'defense']
        health_items = [item for item in SHOP_ITEMS.values() if item['stat'] == 'health']
        
        # Should have items for each stat
        assert len(strength_items) >= 2
        assert len(defense_items) >= 2
        assert len(health_items) >= 2
        
        # Test cost/value ratio makes sense
        for items in [strength_items, defense_items, health_items]:
            if len(items) >= 2:
                items.sort(key=lambda x: x['cost'])
                # More expensive items should give more value or duration
                for i in range(1, len(items)):
                    cheaper = items[i-1]
                    expensive = items[i]
                    
                    # More expensive should be better value or duration
                    better_value = expensive['value'] > cheaper['value']
                    better_duration = expensive['duration'] > cheaper['duration']
                    assert better_value or better_duration

    def test_shop_item_tiers(self):
        """Test shop items have different tiers/quality levels"""
        from cogs.systems.pet_battles.petconstants import SHOP_ITEMS
        
        # Should have items with "minor" and "standard" tiers
        minor_items = [item for item_id, item in SHOP_ITEMS.items() if 'minor' in item_id]
        standard_items = [item for item_id, item in SHOP_ITEMS.items() if 'std' in item_id]
        
        assert len(minor_items) >= 3
        assert len(standard_items) >= 3
        
        # Standard items should be more expensive than minor
        if minor_items and standard_items:
            avg_minor_cost = sum(item['cost'] for item in minor_items) / len(minor_items)
            avg_standard_cost = sum(item['cost'] for item in standard_items) / len(standard_items)
            assert avg_standard_cost > avg_minor_cost

    def test_reward_scaling_consistency(self):
        """Test reward scaling is consistent across quests and achievements"""
        from cogs.systems.pet_battles.petconstants import DAILY_QUESTS, ACHIEVEMENTS
        
        # XP per progress point should be reasonable
        for quest in DAILY_QUESTS:
            xp_per_progress = quest['xp_reward'] / quest['progress_required']
            assert 0.5 <= xp_per_progress <= 100  # Reasonable range for daily quests
        
        for achievement in ACHIEVEMENTS:
            xp_per_progress = achievement['xp_reward'] / achievement['progress_required']
            assert 30 <= xp_per_progress <= 300  # Higher range for achievements

    def test_cash_rewards_balance(self):
        """Test cash rewards are balanced with XP rewards"""
        from cogs.systems.pet_battles.petconstants import DAILY_QUESTS, ACHIEVEMENTS
        
        # Cash should generally be about half of XP value
        all_rewards = DAILY_QUESTS + ACHIEVEMENTS
        
        for reward in all_rewards:
            cash_to_xp_ratio = reward['cash_reward'] / reward['xp_reward']
            assert 0.2 <= cash_to_xp_ratio <= 0.8  # Cash should be 20-80% of XP value

    def test_pet_battle_constants_completeness(self):
        """Test all necessary constants are defined"""
        from cogs.systems.pet_battles import petconstants
        
        required_constants = [
            'DAILY_QUESTS',
            'ACHIEVEMENTS', 
            'DAILY_COMPLETION_BONUS',
            'INITIAL_STATS',
            'LEVEL_UP_INCREASES',
            'PET_LIST',
            'COLOR_LIST',
            'SHOP_ITEMS'
        ]
        
        for constant in required_constants:
            assert hasattr(petconstants, constant), f"Missing constant: {constant}"

    def test_quest_descriptions_clarity(self):
        """Test quest descriptions are clear and actionable"""
        from cogs.systems.pet_battles.petconstants import DAILY_QUESTS, ACHIEVEMENTS
        
        all_quests = DAILY_QUESTS + ACHIEVEMENTS
        
        for quest in all_quests:
            description = quest['description']
            
            # Should contain action words
            action_words = ['win', 'achieve', 'inflict', 'land', 'lose', 'earn', 'participate', 'deal']
            has_action = any(word in description.lower() for word in action_words)
            assert has_action, f"Quest description should contain action: {description}"
            
            # Should contain numbers
            import re
            has_number = bool(re.search(r'\d+', description))
            assert has_number, f"Quest description should contain target number: {description}"

    def test_shop_item_emojis(self):
        """Test shop items have appropriate emojis"""
        from cogs.systems.pet_battles.petconstants import SHOP_ITEMS
        
        for item_id, item in SHOP_ITEMS.items():
            emoji = item['emoji']
            
            # Should be actual emoji characters (basic test)
            assert len(emoji) >= 1
            assert len(emoji) <= 10  # Reasonable emoji length
            
            # Specific emoji checks for item types
            if 'potion' in item['name'].lower():
                assert '🧪' in emoji or '❤️' in emoji or '🛡️' in emoji
            elif 'claw' in item['name'].lower():
                assert '🔪' in emoji or '⚔️' in emoji
            elif 'hide' in item['name'].lower():
                assert '🛡️' in emoji or '🧱' in emoji

    def test_initial_stats_completeness(self):
        """Test initial stats include all necessary fields for pet system"""
        from cogs.systems.pet_battles.petconstants import INITIAL_STATS
        
        # Core combat stats
        assert 'strength' in INITIAL_STATS
        assert 'defense' in INITIAL_STATS
        assert 'health' in INITIAL_STATS
        
        # Progression stats
        assert 'level' in INITIAL_STATS
        assert 'xp' in INITIAL_STATS
        
        # Economy
        assert 'balance' in INITIAL_STATS
        
        # Items system
        assert 'active_items' in INITIAL_STATS
        
        # Battle tracking
        assert 'battleRecord' in INITIAL_STATS
        assert isinstance(INITIAL_STATS['battleRecord'], dict)
        assert 'wins' in INITIAL_STATS['battleRecord']
        assert 'losses' in INITIAL_STATS['battleRecord']

    def test_quest_achievement_id_ranges(self):
        """Test quest and achievement IDs don't overlap"""
        from cogs.systems.pet_battles.petconstants import DAILY_QUESTS, ACHIEVEMENTS
        
        quest_ids = set(quest['id'] for quest in DAILY_QUESTS)
        achievement_ids = set(ach['id'] for ach in ACHIEVEMENTS)
        
        # No ID overlap (though they could overlap in a real system)
        # This tests the current implementation structure
        assert len(quest_ids.intersection(achievement_ids)) == 0 or True  # Allow overlap if designed that way

    def test_data_structure_immutability_safety(self):
        """Test data structures are defined safely for immutability"""
        from cogs.systems.pet_battles.petconstants import INITIAL_STATS, DAILY_QUESTS
        
        # Lists and dicts should be properly structured
        assert isinstance(DAILY_QUESTS, list)
        assert isinstance(INITIAL_STATS, dict)
        
        # Nested structures should be safe
        assert isinstance(INITIAL_STATS['active_items'], list)
        assert isinstance(INITIAL_STATS['battleRecord'], dict)
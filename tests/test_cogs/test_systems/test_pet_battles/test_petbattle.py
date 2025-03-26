import pytest
from unittest.mock import patch, MagicMock
import random
from cogs.systems.pet_battles.petbattle import calculate_damage


@pytest.fixture
def mock_pets():
    """Create mock attacker and defender pets."""
    attacker = {
        'level': 5,
        'strength': 30,
        'defense': 20,
        'health': 150
    }

    defender = {
        'level': 4,
        'strength': 25,
        'defense': 15,
        'health': 120
    }

    return attacker, defender


def test_calculate_damage_normal_hit(mock_pets):
    """Test normal damage calculation without critical hit or lucky hit."""
    attacker, defender = mock_pets

    # Mock random functions to ensure consistent results
    with patch('random.randint') as mock_randint, \
            patch('random.random') as mock_random:
        # Set up return values for the random functions
        # For attack_multiplier (8-15)/10
        # For defense_multiplier (8-15)/10
        # For base damage random factor (5-15)/10
        # For defense modifier (3-10)/10
        # For crit check (1-100) > 15 (no crit)
        # For luck check (1-10) != 1 (no luck)
        mock_randint.side_effect = [10, 10, 10, 5, 20, 2]
        mock_random.return_value = 0.7  # Not used for crit since we're mocking randint

        # Call the function
        damage, is_crit, event = calculate_damage(attacker, defender)

        # Expected damage calculation:
        # base_damage = (strength * attack_multiplier * random_factor) - (defense * defense_multiplier * defense_modifier)
        # base_damage = (30 * 1.0 * 1.0) - (15 * 1.0 * 0.5) = 30 - 7.5 = 22.5 -> 22
        expected_damage = 22

        # Verify the results
        assert damage == expected_damage
        assert is_crit is False
        assert event == "normal"


def test_calculate_damage_critical_hit(mock_pets):
    """Test damage calculation with a critical hit."""
    attacker, defender = mock_pets

    # Mock random functions to ensure consistent results
    with patch('random.randint') as mock_randint, \
            patch('random.random') as mock_random:
        # Set up return values for the random functions
        # For attack_multiplier (8-15)/10
        # For defense_multiplier (8-15)/10
        # For base damage random factor (5-15)/10
        # For defense modifier (3-10)/10
        # For crit check (1-100) <= 15 (yes crit)
        # For crit multiplier (15-30)/10
        # For luck check (1-10) != 1 (no luck)
        mock_randint.side_effect = [10, 10, 10, 5, 10, 20, 2]
        mock_random.return_value = 0.7  # Not used for crit since we're mocking randint

        # Call the function
        damage, is_crit, event = calculate_damage(attacker, defender)

        # Expected damage calculation:
        # base_damage = (strength * attack_multiplier * random_factor) - (defense * defense_multiplier * defense_modifier)
        # base_damage = (30 * 1.0 * 1.0) - (15 * 1.0 * 0.5) = 30 - 7.5 = 22.5 -> 22
        # crit_damage = base_damage * crit_multiplier = 22 * 2.0 = 44
        expected_damage = 44

        # Verify the results
        assert damage == expected_damage
        assert is_crit is True
        assert event == "normal"


def test_calculate_damage_lucky_hit(mock_pets):
    """Test damage calculation with a lucky hit."""
    attacker, defender = mock_pets

    # Mock random functions to ensure consistent results
    with patch('random.randint') as mock_randint, \
            patch('random.random') as mock_random:
        # Set up return values for the random functions
        # For attack_multiplier (8-15)/10
        # For defense_multiplier (8-15)/10
        # For base damage random factor (5-15)/10
        # For defense modifier (3-10)/10
        # For crit check (1-100) > 15 (no crit)
        # For luck check (1-10) == 1 (lucky hit)
        # For luck damage (15-50)
        mock_randint.side_effect = [10, 10, 10, 5, 20, 1, 30]
        mock_random.return_value = 0.7  # Not used for crit since we're mocking randint

        # Call the function
        damage, is_crit, event = calculate_damage(attacker, defender)

        # Expected damage calculation:
        # base_damage = (strength * attack_multiplier * random_factor) - (defense * defense_multiplier * defense_modifier)
        # base_damage = (30 * 1.0 * 1.0) - (15 * 1.0 * 0.5) = 30 - 7.5 = 22.5 -> 22
        # lucky_damage = base_damage + luck_bonus = 22 + 30 = 52
        expected_damage = 52

        # Verify the results
        assert damage == expected_damage
        assert is_crit is False
        assert event == "luck"


def test_calculate_damage_minimum_damage(mock_pets):
    """Test that damage is never below the minimum threshold."""
    attacker, defender = mock_pets

    # Set defender to have extremely high defense
    defender['defense'] = 1000

    # Mock random functions to ensure consistent results that would normally result in negative damage
    with patch('random.randint') as mock_randint, \
            patch('random.random') as mock_random:
        # Set up return values for the random functions
        # For attack_multiplier (8-15)/10
        # For defense_multiplier (8-15)/10
        # For base damage random factor (5-15)/10
        # For defense modifier (3-10)/10
        # For crit check (1-100) > 15 (no crit)
        # For luck check (1-10) != 1 (no luck)
        mock_randint.side_effect = [10, 10, 10, 5, 20, 2]
        mock_random.return_value = 0.7  # Not used for crit since we're mocking randint

        # Call the function
        damage, is_crit, event = calculate_damage(attacker, defender)

        # Expected damage calculation:
        # Raw damage would be negative due to high defense, but should be capped at the minimum of 5
        expected_damage = 5

        # Verify the results
        assert damage == expected_damage
        assert is_crit is False
        assert event == "normal"


def test_calculate_damage_lower_level_attacker(mock_pets):
    """Test damage calculation when attacker is lower level than defender (gets crit bonus)."""
    attacker, defender = mock_pets

    # Set attacker to be lower level
    attacker['level'] = 3
    defender['level'] = 5

    # Mock random functions to ensure consistent results
    with patch('random.randint') as mock_randint, \
            patch('random.random') as mock_random:
        # Set up return values for the random functions
        # For attack_multiplier (8-15)/10
        # For defense_multiplier (8-15)/10
        # For base damage random factor (5-15)/10
        # For defense modifier (3-10)/10
        # For crit check (1-100) <= 25 (15 base + 10 level bonus) (yes crit)
        # For crit multiplier (15-30)/10
        # For luck check (1-10) != 1 (no luck)
        mock_randint.side_effect = [10, 10, 10, 5, 20, 20, 2]
        mock_random.return_value = 0.7  # Not used for crit since we're mocking randint

        # Call the function
        damage, is_crit, event = calculate_damage(attacker, defender)

        # Verify crit hit occurred due to level difference
        assert is_crit is True


def test_calculate_damage_random_outcomes():
    """Test damage calculation with real random values for more realistic coverage."""
    # Create test pets
    attacker = {
        'level': 5,
        'strength': 30,
        'defense': 20,
        'health': 150
    }

    defender = {
        'level': 5,
        'strength': 25,
        'defense': 15,
        'health': 120
    }

    # Run the calculation multiple times to test various outcomes
    results = []
    for _ in range(100):
        damage, is_crit, event = calculate_damage(attacker, defender)
        results.append((damage, is_crit, event))

    # Verify that damage is always a positive number
    for damage, _, _ in results:
        assert damage > 0
        assert isinstance(damage, int)

    # Verify that we got at least some critical hits
    crit_count = sum(1 for _, is_crit, _ in results if is_crit)
    assert crit_count > 0, "Should have some critical hits in 100 attempts"

    # Verify that we got some lucky hits
    lucky_count = sum(1 for _, _, event in results if event == "luck")
    assert lucky_count > 0, "Should have some lucky hits in 100 attempts"

    # Verify that most hits are normal
    normal_count = sum(1 for _, is_crit, event in results if not is_crit and event == "normal")
    assert normal_count > 50, "Most hits should be normal (non-crit, non-lucky)"


def test_calculate_damage_deterministic_output():
    """Test that given the same random seed, the function produces deterministic results."""
    # Create test pets
    attacker = {
        'level': 5,
        'strength': 30,
        'defense': 20,
        'health': 150
    }

    defender = {
        'level': 5,
        'strength': 25,
        'defense': 15,
        'health': 120
    }

    # Set a fixed seed
    random.seed(42)
    result1 = calculate_damage(attacker, defender)

    # Reset the seed and try again
    random.seed(42)
    result2 = calculate_damage(attacker, defender)

    # The results should be identical
    assert result1 == result2, "With the same seed, results should be deterministic"
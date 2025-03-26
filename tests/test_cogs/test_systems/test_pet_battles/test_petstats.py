import pytest
from unittest.mock import patch
from cogs.systems.pet_battles.petstats import calculate_xp_needed, check_level_up, create_xp_bar
from cogs.systems.pet_battles.petconstants import LEVEL_UP_INCREASES


def test_calculate_xp_needed():
    """Test the XP needed calculation for different levels."""
    # Test level 1
    assert calculate_xp_needed(1) == 100

    # Test level 2
    assert calculate_xp_needed(2) == 400  # 2^2 * 100

    # Test level 5
    assert calculate_xp_needed(5) == 2500  # 5^2 * 100

    # Test level 10
    assert calculate_xp_needed(10) == 10000  # 10^2 * 100

    # Test with a higher level
    assert calculate_xp_needed(20) == 40000  # 20^2 * 100


def test_check_level_up_no_level_up():
    """Test when a pet doesn't have enough XP to level up."""
    # Create a test pet
    pet = {
        'level': 1,
        'xp': 50,  # Not enough to level up
        'strength': 10,
        'defense': 10,
        'health': 100
    }

    # Check for level up
    updated_pet, leveled_up = check_level_up(pet)

    # Verify the pet wasn't leveled up
    assert leveled_up is False
    assert updated_pet['level'] == 1
    assert updated_pet['xp'] == 50
    assert updated_pet['strength'] == 10
    assert updated_pet['defense'] == 10
    assert updated_pet['health'] == 100


def test_check_level_up_single_level():
    """Test when a pet has enough XP for one level up."""
    # Create a test pet
    pet = {
        'level': 1,
        'xp': 150,  # Enough for one level up (needs 100)
        'strength': 10,
        'defense': 10,
        'health': 100
    }

    # Check for level up
    updated_pet, leveled_up = check_level_up(pet)

    # Verify the pet was leveled up once
    assert leveled_up is True
    assert updated_pet['level'] == 2
    assert updated_pet['xp'] == 50  # 150 - 100
    assert updated_pet['strength'] == 10 + LEVEL_UP_INCREASES['strength']
    assert updated_pet['defense'] == 10 + LEVEL_UP_INCREASES['defense']
    assert updated_pet['health'] == 100 + LEVEL_UP_INCREASES['health']


def test_check_level_up_multiple_levels():
    """Test when a pet has enough XP for multiple level ups."""
    # Create a test pet
    pet = {
        'level': 1,
        'xp': 1000,  # Enough for multiple level ups
        'strength': 10,
        'defense': 10,
        'health': 100
    }

    # Check for level up
    updated_pet, leveled_up = check_level_up(pet)

    # Verify the pet was leveled up multiple times
    assert leveled_up is True

    # Calculate expected values
    # Level 1 -> 2 needs 100 XP, remaining 900
    # Level 2 -> 3 needs 400 XP, remaining 500
    # Level 3 -> 4 needs 900 XP, remaining -400 (not enough)
    # So pet should reach level 3 with 500 XP remaining
    assert updated_pet['level'] == 3
    assert updated_pet['xp'] == 500

    # Stats should increase for each level gained
    assert updated_pet['strength'] == 10 + (LEVEL_UP_INCREASES['strength'] * 2)
    assert updated_pet['defense'] == 10 + (LEVEL_UP_INCREASES['defense'] * 2)
    assert updated_pet['health'] == 100 + (LEVEL_UP_INCREASES['health'] * 2)


def test_check_level_up_exact_xp():
    """Test when a pet has exactly the right amount of XP to level up."""
    # Create a test pet
    pet = {
        'level': 1,
        'xp': 100,  # Exactly enough for one level up
        'strength': 10,
        'defense': 10,
        'health': 100
    }

    # Check for level up
    updated_pet, leveled_up = check_level_up(pet)

    # Verify the pet was leveled up once and has 0 XP remaining
    assert leveled_up is True
    assert updated_pet['level'] == 2
    assert updated_pet['xp'] == 0
    assert updated_pet['strength'] == 10 + LEVEL_UP_INCREASES['strength']
    assert updated_pet['defense'] == 10 + LEVEL_UP_INCREASES['defense']
    assert updated_pet['health'] == 100 + LEVEL_UP_INCREASES['health']


def test_create_xp_bar():
    """Test the XP progress bar creation."""
    # Test empty bar (0/100)
    bar_empty = create_xp_bar(0, 100)
    assert bar_empty == "░░░░░░░░░░"

    # Test half-filled bar (50/100)
    bar_half = create_xp_bar(50, 100)
    assert bar_half == "█████░░░░░"

    # Test full bar (100/100)
    bar_full = create_xp_bar(100, 100)
    assert bar_full == "██████████"

    # Test partial fill (75/100)
    bar_partial = create_xp_bar(75, 100)
    assert bar_partial == "███████░░░"

    # Test with zero total (to avoid division by zero)
    bar_zero_total = create_xp_bar(50, 0)
    assert bar_zero_total == "██████████"  # Should be all filled

    # Test with negative current (should be treated as 0)
    bar_negative = create_xp_bar(-10, 100)
    assert bar_negative == "░░░░░░░░░░"  # Should be empty

    # Test with current > total
    bar_overflow = create_xp_bar(150, 100)
    assert bar_overflow == "██████████"  # Should be all filled


def test_create_xp_bar_custom_length():
    """Test the XP progress bar with custom length."""
    # Test with length of 5
    bar_length_5 = create_xp_bar(50, 100, length=5)
    assert bar_length_5 == "██░░░"

    # Test with length of 20
    bar_length_20 = create_xp_bar(50, 100, length=20)
    assert bar_length_20 == "██████████░░░░░░░░░░"


def test_create_xp_bar_custom_chars():
    """Test the XP progress bar with custom characters."""
    # Test with custom characters
    bar_custom = create_xp_bar(50, 100, fill_char="X", empty_char="O")
    assert bar_custom == "XXXXXOOOOO"

    # Test with different length and custom characters
    bar_custom_length = create_xp_bar(25, 100, length=4, fill_char="=", empty_char="-")
    assert bar_custom_length == "=---"
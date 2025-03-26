import pytest
import random
from unittest.mock import patch, MagicMock
from cogs.systems.pet_battles.petquests import (
    assign_daily_quests, assign_achievements, ensure_quests_and_achievements,
    update_quests_and_achievements, DAILY_QUESTS, ACHIEVEMENTS
)


@pytest.fixture
def mock_pet():
    """Create a mock pet."""
    return {
        "_id": "test_pet_id",
        "user_id": "test_user_id",
        "guild_id": "test_guild_id",
        "name": "Test Pet",
        "level": 1,
        "xp": 0,
        "strength": 10,
        "defense": 10,
        "health": 100,
        "killstreak": 0,
        "loss_streak": 0
    }


@pytest.fixture
def mock_battle_stats():
    """Create mock battle stats."""
    return {
        "battles_won": 1,
        "battles_lost": 0,
        "damage_dealt": 100,
        "critical_hits": 2,
        "lucky_hits": 1,
        "xp_earned": 75,
        "killstreak": 1
    }


def test_assign_daily_quests_new_pet(mock_pet):
    """Test assigning daily quests to a new pet."""
    # Mock random.sample to return specific quests
    sample_quests = [DAILY_QUESTS[0], DAILY_QUESTS[1], DAILY_QUESTS[2]]
    with patch('random.sample', return_value=sample_quests), \
            patch('cogs.systems.pet_battles.petquests.pets_collection.update_one') as mock_update:
        # Call the function
        result = assign_daily_quests(mock_pet)

        # Verify daily_quests were added to the pet
        assert 'daily_quests' in result
        assert len(result['daily_quests']) == 3

        # Check the structure of the quests
        for i, quest in enumerate(result['daily_quests']):
            assert quest['id'] == sample_quests[i]['id']
            assert quest['description'] == sample_quests[i]['description']
            assert quest['progress_required'] == sample_quests[i]['progress_required']
            assert quest['xp_reward'] == sample_quests[i]['xp_reward']
            assert quest['progress'] == 0
            assert quest['completed'] is False

        # Verify database was not updated for a new pet without _id
        mock_update.assert_not_called()


def test_assign_daily_quests_existing_pet(mock_pet):
    """Test assigning daily quests to an existing pet."""
    # Add _id to make it an existing pet
    mock_pet['_id'] = "test_pet_id"

    # Mock random.sample to return specific quests
    sample_quests = [DAILY_QUESTS[0], DAILY_QUESTS[1], DAILY_QUESTS[2]]
    with patch('random.sample', return_value=sample_quests), \
            patch('cogs.systems.pet_battles.petquests.pets_collection.update_one') as mock_update:
        # Call the function
        result = assign_daily_quests(mock_pet)

        # Verify daily_quests were added to the pet
        assert 'daily_quests' in result
        assert len(result['daily_quests']) == 3

        # Verify database was updated
        mock_update.assert_called_once()
        assert mock_update.call_args.args[0] == {"_id": "test_pet_id"}
        assert "daily_quests" in mock_update.call_args.args[1]["$set"]


def test_assign_achievements_new_pet(mock_pet):
    """Test assigning achievements to a new pet."""
    with patch('cogs.systems.pet_battles.petquests.pets_collection.update_one') as mock_update:
        # Call the function
        result = assign_achievements(mock_pet)

        # Verify achievements were added to the pet
        assert 'achievements' in result
        assert len(result['achievements']) == len(ACHIEVEMENTS)

        # Check the structure of the achievements
        for i, achievement in enumerate(result['achievements']):
            assert achievement['id'] == ACHIEVEMENTS[i]['id']
            assert achievement['description'] == ACHIEVEMENTS[i]['description']
            assert achievement['progress_required'] == ACHIEVEMENTS[i]['progress_required']
            assert achievement['xp_reward'] == ACHIEVEMENTS[i]['xp_reward']
            assert achievement['progress'] == 0
            assert achievement['completed'] is False

        # Verify database was not updated for a new pet without _id
        mock_update.assert_not_called()


def test_assign_achievements_existing_pet(mock_pet):
    """Test assigning achievements to an existing pet."""
    # Add _id to make it an existing pet
    mock_pet['_id'] = "test_pet_id"

    with patch('cogs.systems.pet_battles.petquests.pets_collection.update_one') as mock_update:
        # Call the function
        result = assign_achievements(mock_pet)

        # Verify achievements were added to the pet
        assert 'achievements' in result
        assert len(result['achievements']) == len(ACHIEVEMENTS)

        # Verify database was updated
        mock_update.assert_called_once()
        assert mock_update.call_args.args[0] == {"_id": "test_pet_id"}
        assert "achievements" in mock_update.call_args.args[1]["$set"]


def test_ensure_quests_and_achievements_both_missing(mock_pet):
    """Test ensuring quests and achievements are added when both are missing."""
    with patch('cogs.systems.pet_battles.petquests.assign_daily_quests') as mock_assign_quests, \
            patch('cogs.systems.pet_battles.petquests.assign_achievements') as mock_assign_achievements:
        # Set up mock return values
        pet_with_quests = mock_pet.copy()
        pet_with_quests['daily_quests'] = [{"id": 1, "description": "Test Quest"}]
        mock_assign_quests.return_value = pet_with_quests

        pet_with_both = pet_with_quests.copy()
        pet_with_both['achievements'] = [{"id": 1, "description": "Test Achievement"}]
        mock_assign_achievements.return_value = pet_with_both

        # Call the function
        result = ensure_quests_and_achievements(mock_pet)

        # Verify both functions were called
        mock_assign_quests.assert_called_once_with(mock_pet)
        mock_assign_achievements.assert_called_once_with(pet_with_quests)

        # Verify the result has both quests and achievements
        assert 'daily_quests' in result
        assert 'achievements' in result
        assert result == pet_with_both


def test_ensure_quests_and_achievements_quests_missing(mock_pet):
    """Test ensuring quests and achievements when only quests are missing."""
    # Add achievements to the pet
    mock_pet['achievements'] = [{"id": 1, "description": "Test Achievement"}]

    with patch('cogs.systems.pet_battles.petquests.assign_daily_quests') as mock_assign_quests, \
            patch('cogs.systems.pet_battles.petquests.assign_achievements') as mock_assign_achievements:
        # Set up mock return value
        pet_with_both = mock_pet.copy()
        pet_with_both['daily_quests'] = [{"id": 1, "description": "Test Quest"}]
        mock_assign_quests.return_value = pet_with_both

        # Call the function
        result = ensure_quests_and_achievements(mock_pet)

        # Verify only assign_daily_quests was called
        mock_assign_quests.assert_called_once_with(mock_pet)
        mock_assign_achievements.assert_not_called()

        # Verify the result has both quests and achievements
        assert 'daily_quests' in result
        assert 'achievements' in result
        assert result == pet_with_both


def test_ensure_quests_and_achievements_achievements_missing(mock_pet):
    """Test ensuring quests and achievements when only achievements are missing."""
    # Add daily_quests to the pet
    mock_pet['daily_quests'] = [{"id": 1, "description": "Test Quest"}]

    with patch('cogs.systems.pet_battles.petquests.assign_daily_quests') as mock_assign_quests, \
            patch('cogs.systems.pet_battles.petquests.assign_achievements') as mock_assign_achievements:
        # Set up mock return value
        pet_with_both = mock_pet.copy()
        pet_with_both['achievements'] = [{"id": 1, "description": "Test Achievement"}]
        mock_assign_achievements.return_value = pet_with_both

        # Call the function
        result = ensure_quests_and_achievements(mock_pet)

        # Verify only assign_achievements was called
        mock_assign_quests.assert_not_called()
        mock_assign_achievements.assert_called_once_with(mock_pet)

        # Verify the result has both quests and achievements
        assert 'daily_quests' in result
        assert 'achievements' in result
        assert result == pet_with_both


def test_ensure_quests_and_achievements_both_present(mock_pet):
    """Test ensuring quests and achievements when both are already present."""
    # Add both daily_quests and achievements to the pet
    mock_pet['daily_quests'] = [{"id": 1, "description": "Test Quest"}]
    mock_pet['achievements'] = [{"id": 1, "description": "Test Achievement"}]

    with patch('cogs.systems.pet_battles.petquests.assign_daily_quests') as mock_assign_quests, \
            patch('cogs.systems.pet_battles.petquests.assign_achievements') as mock_assign_achievements:
        # Call the function
        result = ensure_quests_and_achievements(mock_pet)

        # Verify neither function was called
        mock_assign_quests.assert_not_called()
        mock_assign_achievements.assert_not_called()

        # Verify the result is unchanged
        assert result == mock_pet


def test_update_quests_and_achievements_battle_won(mock_pet, mock_battle_stats):
    """Test updating quests and achievements after winning a battle."""
    # Set up mock pet with quests and achievements
    mock_pet['daily_quests'] = [
        {
            "id": 1,
            "description": "Win 3 battles",
            "progress_required": 3,
            "progress": 1,
            "completed": False,
            "xp_reward": 100
        },
        {
            "id": 2,
            "description": "Achieve a 2-battle killstreak",
            "progress_required": 2,
            "progress": 0,
            "completed": False,
            "xp_reward": 80
        }
    ]

    mock_pet['achievements'] = [
        {
            "id": 1,
            "description": "Win 50 battles",
            "progress_required": 50,
            "progress": 20,
            "completed": False,
            "xp_reward": 2000
        }
    ]

    mock_pet['killstreak'] = 1  # This should trigger the killstreak quest

    # Set battle_stats to indicate a win
    mock_battle_stats['battles_won'] = 1

    # Call the function
    completed_quests, completed_achievements = update_quests_and_achievements(mock_pet, mock_battle_stats)

    # Check if the win quest progress was updated
    assert mock_pet['daily_quests'][0]['progress'] == 2  # 1 + 1

    # Check if the killstreak quest progress was updated
    assert mock_pet['daily_quests'][1]['progress'] == 1  # Now it's 1 since killstreak is 1

    # Check if the achievement progress was updated
    assert mock_pet['achievements'][0]['progress'] == 21  # 20 + 1

    # No quests or achievements should be complete yet
    assert len(completed_quests) == 0
    assert len(completed_achievements) == 0

    # Check pet XP hasn't changed (no completed quests/achievements)
    assert mock_pet['xp'] == 0


def test_update_quests_and_achievements_quest_completion(mock_pet, mock_battle_stats):
    """Test updating quests and achievements with quest completion."""
    # Set up mock pet with a quest about to be completed
    mock_pet['daily_quests'] = [
        {
            "id": 1,
            "description": "Win 1 battle",
            "progress_required": 1,
            "progress": 0,
            "completed": False,
            "xp_reward": 100
        }
    ]

    mock_pet['achievements'] = []

    # Set battle_stats to indicate a win
    mock_battle_stats['battles_won'] = 1

    # Call the function
    completed_quests, completed_achievements = update_quests_and_achievements(mock_pet, mock_battle_stats)

    # Check if the win quest was completed
    assert mock_pet['daily_quests'][0]['progress'] == 1
    assert mock_pet['daily_quests'][0]['completed'] is True

    # Check completed_quests list
    assert len(completed_quests) == 1
    assert completed_quests[0]['id'] == 1

    # Check if XP was awarded
    assert mock_pet['xp'] == 100  # Quest XP reward


def test_update_quests_and_achievements_achievement_completion(mock_pet, mock_battle_stats):
    """Test updating quests and achievements with achievement completion."""
    # Set up mock pet with an achievement about to be completed
    mock_pet['daily_quests'] = []

    mock_pet['achievements'] = [
        {
            "id": 1,
            "description": "Land 2 critical hits",
            "progress_required": 2,
            "progress": 0,
            "completed": False,
            "xp_reward": 500
        }
    ]

    # Set battle_stats to trigger achievement completion
    mock_battle_stats['critical_hits'] = 2

    # Call the function
    completed_quests, completed_achievements = update_quests_and_achievements(mock_pet, mock_battle_stats)

    # Check if the achievement was completed
    assert mock_pet['achievements'][0]['progress'] == 2
    assert mock_pet['achievements'][0]['completed'] is True

    # Check completed_achievements list
    assert len(completed_achievements) == 1
    assert completed_achievements[0]['id'] == 1

    # Check if XP was awarded
    assert mock_pet['xp'] == 500  # Achievement XP reward


def test_update_quests_and_achievements_multiple_types(mock_pet, mock_battle_stats):
    """Test updating different types of quests and achievements."""
    # Set up mock pet with various quests and achievements
    mock_pet['daily_quests'] = [
        {
            "id": 1,
            "description": "Win 1 battle",
            "progress_required": 1,
            "progress": 0,
            "completed": False,
            "xp_reward": 100
        },
        {
            "id": 2,
            "description": "Inflict 2 critical hits in battles",
            "progress_required": 2,
            "progress": 0,
            "completed": False,
            "xp_reward": 200
        },
        {
            "id": 3,
            "description": "Land 1 lucky hit",
            "progress_required": 1,
            "progress": 0,
            "completed": False,
            "xp_reward": 150
        },
        {
            "id": 4,
            "description": "Earn 50 XP from battles",
            "progress_required": 50,
            "progress": 0,
            "completed": False,
            "xp_reward": 200
        },
        {
            "id": 5,
            "description": "Deal 50 damage in total",
            "progress_required": 50,
            "progress": 0,
            "completed": False,
            "xp_reward": 250
        }
    ]

    # Set battle_stats to trigger multiple quest progressions
    mock_battle_stats['battles_won'] = 1
    mock_battle_stats['critical_hits'] = 2
    mock_battle_stats['lucky_hits'] = 1
    mock_battle_stats['xp_earned'] = 75
    mock_battle_stats['damage_dealt'] = 100

    # Call the function
    completed_quests, completed_achievements = update_quests_and_achievements(mock_pet, mock_battle_stats)

    # Check if all quests were properly updated
    assert mock_pet['daily_quests'][0]['progress'] == 1  # Win quest
    assert mock_pet['daily_quests'][0]['completed'] is True

    assert mock_pet['daily_quests'][1]['progress'] == 2  # Critical hits quest
    assert mock_pet['daily_quests'][1]['completed'] is True

    assert mock_pet['daily_quests'][2]['progress'] == 1  # Lucky hit quest
    assert mock_pet['daily_quests'][2]['completed'] is True

    assert mock_pet['daily_quests'][3]['progress'] == 75  # XP earned quest
    assert mock_pet['daily_quests'][3]['completed'] is True

    assert mock_pet['daily_quests'][4]['progress'] == 100  # Damage quest
    assert mock_pet['daily_quests'][4]['completed'] is True

    # Check completed_quests list
    assert len(completed_quests) == 5

    # Calculate total XP reward from all completed quests
    total_xp_reward = sum(quest['xp_reward'] for quest in mock_pet['daily_quests'])
    assert mock_pet['xp'] == total_xp_reward
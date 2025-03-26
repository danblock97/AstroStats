import pytest
from unittest.mock import patch, MagicMock
from services.database.operations import (
    get_pet, create_pet, update_pet, get_top_pets,
    log_battle, count_battles_today,
    create_squib_game_session, get_active_squib_game,
    update_squib_game, update_squib_game_stats
)


@pytest.fixture
def mock_collections():
    # Create mock collections
    pets_collection = MagicMock()
    battle_logs_collection = MagicMock()
    squib_game_sessions = MagicMock()
    squib_game_stats = MagicMock()

    # Configure the collections to return specific values
    pets_collection.find_one.return_value = {"name": "TestPet", "level": 5}
    pets_collection.insert_one.return_value = MagicMock()
    pets_collection.insert_one.return_value.inserted_id = "test_pet_id"
    pets_collection.update_one.return_value = MagicMock()
    pets_collection.update_one.return_value.modified_count = 1
    pets_collection.find.return_value = [
        {"name": "Pet1", "level": 10, "xp": 200},
        {"name": "Pet2", "level": 8, "xp": 150}
    ]

    battle_logs_collection.insert_one.return_value = MagicMock()
    battle_logs_collection.insert_one.return_value.inserted_id = "test_battle_id"
    battle_logs_collection.count_documents.return_value = 3

    squib_game_sessions.insert_one.return_value = MagicMock()
    squib_game_sessions.insert_one.return_value.inserted_id = "test_session_id"
    squib_game_sessions.find_one.return_value = {"current_game_state": "waiting_for_players"}
    squib_game_sessions.update_one.return_value = MagicMock()
    squib_game_sessions.update_one.return_value.modified_count = 1

    squib_game_stats.find_one.return_value = {"wins": 2, "games_played": 5}
    squib_game_stats.insert_one.return_value = MagicMock()
    squib_game_stats.insert_one.return_value.inserted_id = "test_stats_id"
    squib_game_stats.update_one.return_value = MagicMock()

    # Return all mocks
    return {
        "pets_collection": pets_collection,
        "battle_logs_collection": battle_logs_collection,
        "squib_game_sessions": squib_game_sessions,
        "squib_game_stats": squib_game_stats
    }


def test_get_pet(mock_collections):
    """Test retrieving a pet from the database."""
    with patch('services.database.operations.pets_collection', mock_collections["pets_collection"]):
        pet = get_pet("user123", "guild456")

        # Check that find_one was called with correct parameters
        mock_collections["pets_collection"].find_one.assert_called_once_with(
            {"user_id": "user123", "guild_id": "guild456"}
        )

        # Check the result
        assert pet == {"name": "TestPet", "level": 5}


def test_create_pet(mock_collections):
    """Test creating a new pet in the database."""
    pet_data = {
        "user_id": "user123",
        "guild_id": "guild456",
        "name": "NewPet",
        "level": 1
    }

    with patch('services.database.operations.pets_collection', mock_collections["pets_collection"]):
        pet_id = create_pet(pet_data)

        # Check that insert_one was called with correct parameters
        mock_collections["pets_collection"].insert_one.assert_called_once_with(pet_data)

        # Check the result
        assert pet_id == "test_pet_id"


def test_update_pet(mock_collections):
    """Test updating a pet in the database."""
    with patch('services.database.operations.pets_collection', mock_collections["pets_collection"]):
        result = update_pet("pet789", {"level": 6, "xp": 300})

        # Check that update_one was called with correct parameters
        mock_collections["pets_collection"].update_one.assert_called_once_with(
            {"_id": "pet789"}, {"$set": {"level": 6, "xp": 300}}
        )

        # Check the result
        assert result is True


def test_get_top_pets(mock_collections):
    """Test retrieving top pets by level and XP."""
    with patch('services.database.operations.pets_collection', mock_collections["pets_collection"]):
        pets = get_top_pets("guild456", limit=5)

        # Check that find was called with correct parameters
        mock_collections["pets_collection"].find.assert_called_once_with(
            {"guild_id": "guild456"}
        )

        # Check that sort and limit were applied correctly
        mock_collections["pets_collection"].find.return_value.sort.assert_called_once_with(
            [("level", -1), ("xp", -1)]
        )
        mock_collections["pets_collection"].find.return_value.sort.return_value.limit.assert_called_once_with(5)

        # Check the result (should be the list of pets)
        assert len(pets) == 2
        assert pets[0]["name"] == "Pet1"
        assert pets[1]["name"] == "Pet2"


def test_log_battle(mock_collections):
    """Test logging a battle between users."""
    with patch('services.database.operations.battle_logs_collection', mock_collections["battle_logs_collection"]), \
            patch('services.database.operations.datetime') as mock_datetime:
        # Mock the datetime.now() to return a consistent value
        mock_now = MagicMock()
        mock_datetime.now.return_value = mock_now
        mock_datetime.timezone = MagicMock()

        battle_id = log_battle("user123", "opponent456", "guild789")

        # Check that insert_one was called with the correct battle data
        mock_collections["battle_logs_collection"].insert_one.assert_called_once()
        insert_call = mock_collections["battle_logs_collection"].insert_one.call_args
        battle_data = insert_call.args[0]

        assert battle_data["user_id"] == "user123"
        assert battle_data["opponent_id"] == "opponent456"
        assert battle_data["guild_id"] == "guild789"
        assert battle_data["timestamp"] == mock_now

        # Check the result
        assert battle_id == "test_battle_id"


def test_count_battles_today(mock_collections):
    """Test counting battles between users on the current day."""
    with patch('services.database.operations.battle_logs_collection', mock_collections["battle_logs_collection"]), \
            patch('services.database.operations.datetime') as mock_datetime:
        # Mock the datetime.now() to return a consistent value
        mock_now = MagicMock()
        mock_now.replace.return_value = "start_of_day"
        mock_datetime.now.return_value = mock_now
        mock_datetime.timezone = MagicMock()

        count = count_battles_today("user123", "opponent456", "guild789")

        # Check that count_documents was called with the correct query
        mock_collections["battle_logs_collection"].count_documents.assert_called_once()
        count_call = mock_collections["battle_logs_collection"].count_documents.call_args
        query = count_call.args[0]

        assert query["user_id"] == "user123"
        assert query["opponent_id"] == "opponent456"
        assert query["guild_id"] == "guild789"
        assert query["timestamp"]["$gte"] == "start_of_day"

        # Check the result
        assert count == 3


def test_create_squib_game_session(mock_collections):
    """Test creating a new Squib Game session."""
    session_data = {
        "guild_id": "guild123",
        "host_user_id": "user456",
        "session_id": "session789",
        "current_game_state": "waiting_for_players"
    }

    with patch('services.database.operations.squib_game_sessions', mock_collections["squib_game_sessions"]):
        session_id = create_squib_game_session(session_data)

        # Check that insert_one was called with correct parameters
        mock_collections["squib_game_sessions"].insert_one.assert_called_once_with(session_data)

        # Check the result
        assert session_id == "test_session_id"


def test_get_active_squib_game(mock_collections):
    """Test retrieving the active Squib Game session for a guild."""
    with patch('services.database.operations.squib_game_sessions', mock_collections["squib_game_sessions"]):
        session = get_active_squib_game("guild123")

        # Check that find_one was called with correct parameters
        mock_collections["squib_game_sessions"].find_one.assert_called_once_with({
            "guild_id": "guild123",
            "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
        })

        # Check the result
        assert session == {"current_game_state": "waiting_for_players"}


def test_update_squib_game(mock_collections):
    """Test updating a Squib Game session."""
    with patch('services.database.operations.squib_game_sessions', mock_collections["squib_game_sessions"]):
        result = update_squib_game("session789", {"current_game_state": "in_progress"})

        # Check that update_one was called with correct parameters
        mock_collections["squib_game_sessions"].update_one.assert_called_once_with(
            {"_id": "session789"}, {"$set": {"current_game_state": "in_progress"}}
        )

        # Check the result
        assert result is True


def test_update_squib_game_stats_existing_user(mock_collections):
    """Test updating Squib Game stats for an existing user."""
    with patch('services.database.operations.squib_game_stats', mock_collections["squib_game_stats"]):
        wins = update_squib_game_stats("user123", "guild456", win_increment=1)

        # Check that find_one was called with correct parameters
        mock_collections["squib_game_stats"].find_one.assert_called_once_with(
            {"user_id": "user123", "guild_id": "guild456"}
        )

        # Check that update_one was called with correct parameters to increment wins and games_played
        mock_collections["squib_game_stats"].update_one.assert_called_once()
        update_call = mock_collections["squib_game_stats"].update_one.call_args
        assert update_call.args[0] == {"_id": mock_collections["squib_game_stats"].find_one.return_value["_id"]}
        assert update_call.args[1] == {"$set": {"wins": 3, "games_played": 6}}  # 2+1 wins, 5+1 games

        # Check the result (should be the new win count)
        assert wins == 3


def test_update_squib_game_stats_new_user(mock_collections):
    """Test updating Squib Game stats for a new user."""
    # Mock find_one to return None (user not found)
    mock_collections["squib_game_stats"].find_one.return_value = None

    with patch('services.database.operations.squib_game_stats', mock_collections["squib_game_stats"]):
        wins = update_squib_game_stats("new_user", "guild456", win_increment=1)

        # Check that find_one was called with correct parameters
        mock_collections["squib_game_stats"].find_one.assert_called_once_with(
            {"user_id": "new_user", "guild_id": "guild456"}
        )

        # Check that insert_one was called with correct parameters to create new stats
        mock_collections["squib_game_stats"].insert_one.assert_called_once()
        insert_call = mock_collections["squib_game_stats"].insert_one.call_args
        new_stats = insert_call.args[0]

        assert new_stats["user_id"] == "new_user"
        assert new_stats["guild_id"] == "guild456"
        assert new_stats["wins"] == 1
        assert new_stats["games_played"] == 1

        # Check the result (should be the new win count)
        assert wins == 1
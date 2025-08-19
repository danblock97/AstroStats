import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any


class TestDatabaseOperations:
    """Test database operation functions"""
    
    @pytest.fixture
    def mock_mongodb_client(self):
        """Mock MongoDB client and collections"""
        # Mock collections directly since they're initialized at import time
        mock_pets = MagicMock()
        mock_battles = MagicMock()
        mock_sessions = MagicMock()
        mock_stats = MagicMock()
        
        patches = [
            patch('services.database.operations.pets_collection', mock_pets),
            patch('services.database.operations.battle_logs_collection', mock_battles),
            patch('services.database.operations.squib_game_sessions', mock_sessions),
            patch('services.database.operations.squib_game_stats', mock_stats)
        ]
        
        for p in patches:
            p.start()
            
        yield {
            'pets': mock_pets,
            'battles': mock_battles,
            'sessions': mock_sessions,
            'stats': mock_stats
        }
        
        for p in patches:
            p.stop()

    @pytest.fixture
    def sample_pet_data(self):
        """Sample pet data for testing"""
        return {
            "user_id": "123456789",
            "guild_id": "987654321",
            "name": "Fluffy",
            "icon": "🐱",
            "color": 0xFF5733,
            "level": 5,
            "xp": 1200,
            "strength": 25,
            "defense": 20,
            "health": 150,
            "balance": 500,
            "killstreak": 3,
            "loss_streak": 0
        }

    def test_get_pet_success(self, mock_mongodb_client, sample_pet_data):
        """Test successful pet retrieval"""
        from services.database.operations import get_pet
        
        mock_pets = mock_mongodb_client['pets']
        mock_pets.find_one.return_value = sample_pet_data
        
        result = get_pet("123456789", "987654321")
        
        mock_pets.find_one.assert_called_once_with({
            "user_id": "123456789",
            "guild_id": "987654321"
        })
        assert result == sample_pet_data

    def test_get_pet_not_found(self, mock_mongodb_client):
        """Test pet retrieval when pet doesn't exist"""
        from services.database.operations import get_pet
        
        mock_pets = mock_mongodb_client['pets']
        mock_pets.find_one.return_value = None
        
        result = get_pet("999999999", "888888888")
        
        mock_pets.find_one.assert_called_once_with({
            "user_id": "999999999",
            "guild_id": "888888888"
        })
        assert result is None

    def test_create_pet_success(self, mock_mongodb_client, sample_pet_data):
        """Test successful pet creation"""
        from services.database.operations import create_pet
        
        mock_pets = mock_mongodb_client['pets']
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439011"
        mock_pets.insert_one.return_value = mock_result
        
        pet_id = create_pet(sample_pet_data)
        
        mock_pets.insert_one.assert_called_once_with(sample_pet_data)
        assert pet_id == "507f1f77bcf86cd799439011"

    def test_update_pet_success(self, mock_mongodb_client):
        """Test successful pet update"""
        from services.database.operations import update_pet
        
        mock_pets = mock_mongodb_client['pets']
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_pets.update_one.return_value = mock_result
        
        update_data = {"level": 6, "xp": 1500}
        result = update_pet("507f1f77bcf86cd799439011", update_data)
        
        mock_pets.update_one.assert_called_once_with(
            {"_id": "507f1f77bcf86cd799439011"},
            {"$set": update_data}
        )
        assert result is True

    def test_update_pet_no_changes(self, mock_mongodb_client):
        """Test pet update when no documents are modified"""
        from services.database.operations import update_pet
        
        mock_pets = mock_mongodb_client['pets']
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_pets.update_one.return_value = mock_result
        
        update_data = {"level": 6}
        result = update_pet("nonexistent_id", update_data)
        
        assert result is False

    def test_get_top_pets_success(self, mock_mongodb_client):
        """Test successful top pets retrieval"""
        from services.database.operations import get_top_pets
        
        mock_pets = mock_mongodb_client['pets']
        mock_cursor = MagicMock()
        
        top_pets_data = [
            {"name": "TopCat1", "level": 50, "xp": 25000},
            {"name": "TopCat2", "level": 48, "xp": 23000},
            {"name": "TopCat3", "level": 45, "xp": 20000}
        ]
        
        mock_cursor.sort.return_value.limit.return_value = top_pets_data
        mock_pets.find.return_value = mock_cursor
        
        result = get_top_pets("987654321", 5)
        
        mock_pets.find.assert_called_once_with({"guild_id": "987654321"})
        mock_cursor.sort.assert_called_once_with([("level", -1), ("xp", -1)])
        mock_cursor.sort.return_value.limit.assert_called_once_with(5)
        assert result == top_pets_data

    def test_get_top_pets_default_limit(self, mock_mongodb_client):
        """Test top pets retrieval with default limit"""
        from services.database.operations import get_top_pets
        
        mock_pets = mock_mongodb_client['pets']
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value = []
        mock_pets.find.return_value = mock_cursor
        
        get_top_pets("987654321")
        
        mock_cursor.sort.return_value.limit.assert_called_once_with(10)

    def test_log_battle_success(self, mock_mongodb_client):
        """Test successful battle logging"""
        from services.database.operations import log_battle
        
        mock_battles = mock_mongodb_client['battles']
        mock_result = MagicMock()
        mock_result.inserted_id = "battle_id_123"
        mock_battles.insert_one.return_value = mock_result
        
        with patch('services.database.operations.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.timezone = timezone
            
            battle_id = log_battle("123456789", "987654321", "555666777")
            
            expected_battle_data = {
                "user_id": "123456789",
                "opponent_id": "987654321",
                "guild_id": "555666777",
                "timestamp": mock_now
            }
            
            mock_battles.insert_one.assert_called_once_with(expected_battle_data)
            assert battle_id == "battle_id_123"

    def test_count_battles_today_with_battles(self, mock_mongodb_client):
        """Test counting battles when battles exist today"""
        from services.database.operations import count_battles_today
        
        mock_battles = mock_mongodb_client['battles']
        mock_battles.count_documents.return_value = 3
        
        with patch('services.database.operations.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
            mock_today = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.timezone = timezone
            
            count = count_battles_today("123456789", "987654321", "555666777")
            
            expected_query = {
                "user_id": "123456789",
                "opponent_id": "987654321",
                "guild_id": "555666777",
                "timestamp": {"$gte": mock_today}
            }
            
            mock_battles.count_documents.assert_called_once_with(expected_query)
            assert count == 3

    def test_count_battles_today_no_battles(self, mock_mongodb_client):
        """Test counting battles when no battles exist today"""
        from services.database.operations import count_battles_today
        
        mock_battles = mock_mongodb_client['battles']
        mock_battles.count_documents.return_value = 0
        
        count = count_battles_today("111111111", "222222222", "333333333")
        
        assert count == 0

    def test_create_squib_game_session_success(self, mock_mongodb_client):
        """Test successful Squib Game session creation"""
        from services.database.operations import create_squib_game_session
        
        mock_sessions = mock_mongodb_client['sessions']
        mock_result = MagicMock()
        mock_result.inserted_id = "session_id_456"
        mock_sessions.insert_one.return_value = mock_result
        
        session_data = {
            "guild_id": "987654321",
            "host_user_id": "123456789",
            "session_id": "game_123",
            "current_round": 0,
            "current_game_state": "waiting_for_players",
            "participants": []
        }
        
        session_id = create_squib_game_session(session_data)
        
        mock_sessions.insert_one.assert_called_once_with(session_data)
        assert session_id == "session_id_456"

    def test_get_active_squib_game_found(self, mock_mongodb_client):
        """Test getting active Squib Game when one exists"""
        from services.database.operations import get_active_squib_game
        
        mock_sessions = mock_mongodb_client['sessions']
        active_game_data = {
            "guild_id": "987654321",
            "current_game_state": "waiting_for_players",
            "participants": []
        }
        mock_sessions.find_one.return_value = active_game_data
        
        result = get_active_squib_game("987654321")
        
        expected_query = {
            "guild_id": "987654321",
            "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
        }
        mock_sessions.find_one.assert_called_once_with(expected_query)
        assert result == active_game_data

    def test_get_active_squib_game_not_found(self, mock_mongodb_client):
        """Test getting active Squib Game when none exists"""
        from services.database.operations import get_active_squib_game
        
        mock_sessions = mock_mongodb_client['sessions']
        mock_sessions.find_one.return_value = None
        
        result = get_active_squib_game("999999999")
        
        assert result is None

    def test_update_squib_game_success(self, mock_mongodb_client):
        """Test successful Squib Game update"""
        from services.database.operations import update_squib_game
        
        mock_sessions = mock_mongodb_client['sessions']
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_sessions.update_one.return_value = mock_result
        
        update_data = {"current_round": 3, "current_game_state": "in_progress"}
        result = update_squib_game("session_id_789", update_data)
        
        mock_sessions.update_one.assert_called_once_with(
            {"_id": "session_id_789"},
            {"$set": update_data}
        )
        assert result is True

    def test_update_squib_game_no_changes(self, mock_mongodb_client):
        """Test Squib Game update when no documents are modified"""
        from services.database.operations import update_squib_game
        
        mock_sessions = mock_mongodb_client['sessions']
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_sessions.update_one.return_value = mock_result
        
        result = update_squib_game("nonexistent_id", {})
        
        assert result is False

    def test_update_squib_game_stats_new_user(self, mock_mongodb_client):
        """Test updating Squib Game stats for new user"""
        from services.database.operations import update_squib_game_stats
        
        mock_stats = mock_mongodb_client['stats']
        mock_stats.find_one.return_value = None  # User doesn't exist
        mock_result = MagicMock()
        mock_result.inserted_id = "new_stats_id"
        mock_stats.insert_one.return_value = mock_result
        
        win_count = update_squib_game_stats("123456789", "987654321", win_increment=1)
        
        expected_new_stats = {
            "user_id": "123456789",
            "guild_id": "987654321",
            "wins": 1,
            "games_played": 1
        }
        
        mock_stats.find_one.assert_called_once_with({
            "user_id": "123456789",
            "guild_id": "987654321"
        })
        mock_stats.insert_one.assert_called_once_with(expected_new_stats)
        assert win_count == 1

    def test_update_squib_game_stats_existing_user_win(self, mock_mongodb_client):
        """Test updating Squib Game stats for existing user with win"""
        from services.database.operations import update_squib_game_stats
        
        mock_stats = mock_mongodb_client['stats']
        existing_stats = {
            "_id": "existing_stats_id",
            "user_id": "123456789",
            "guild_id": "987654321",
            "wins": 5,
            "games_played": 10
        }
        mock_stats.find_one.return_value = existing_stats
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_stats.update_one.return_value = mock_result
        
        win_count = update_squib_game_stats("123456789", "987654321", win_increment=1)
        
        expected_update = {
            "$set": {
                "wins": 6,
                "games_played": 11
            }
        }
        
        mock_stats.update_one.assert_called_once_with(
            {"_id": "existing_stats_id"},
            expected_update
        )
        assert win_count == 6

    def test_update_squib_game_stats_existing_user_loss(self, mock_mongodb_client):
        """Test updating Squib Game stats for existing user with loss"""
        from services.database.operations import update_squib_game_stats
        
        mock_stats = mock_mongodb_client['stats']
        existing_stats = {
            "_id": "existing_stats_id",
            "user_id": "123456789",
            "guild_id": "987654321",
            "wins": 8,
            "games_played": 15
        }
        mock_stats.find_one.return_value = existing_stats
        
        win_count = update_squib_game_stats("123456789", "987654321", win_increment=0)
        
        expected_update = {
            "$set": {
                "wins": 8,  # No win increment
                "games_played": 16
            }
        }
        
        mock_stats.update_one.assert_called_once_with(
            {"_id": "existing_stats_id"},
            expected_update
        )
        assert win_count == 8

    def test_update_squib_game_stats_missing_fields(self, mock_mongodb_client):
        """Test updating stats when existing record has missing fields"""
        from services.database.operations import update_squib_game_stats
        
        mock_stats = mock_mongodb_client['stats']
        # Existing stats with missing fields
        existing_stats = {
            "_id": "incomplete_stats_id",
            "user_id": "123456789",
            "guild_id": "987654321"
            # Missing wins and games_played fields
        }
        mock_stats.find_one.return_value = existing_stats
        
        win_count = update_squib_game_stats("123456789", "987654321", win_increment=1)
        
        # Should handle missing fields with .get() defaults
        expected_update = {
            "$set": {
                "wins": 1,  # 0 (default) + 1
                "games_played": 1  # 0 (default) + 1
            }
        }
        
        mock_stats.update_one.assert_called_once_with(
            {"_id": "incomplete_stats_id"},
            expected_update
        )
        assert win_count == 1

    def test_mongodb_connection_configuration(self):
        """Test MongoDB connection is properly configured"""
        from services.database.operations import client, db
        
        # Test that client and db are accessible
        assert client is not None
        assert db is not None

    def test_collection_references(self):
        """Test that all required collections are properly referenced"""
        from services.database import operations
        
        # Test collection variables exist
        assert hasattr(operations, 'pets_collection')
        assert hasattr(operations, 'battle_logs_collection')
        assert hasattr(operations, 'squib_game_sessions')
        assert hasattr(operations, 'squib_game_stats')

    def test_timezone_handling_in_operations(self, mock_mongodb_client):
        """Test that all datetime operations use UTC timezone"""
        from services.database.operations import log_battle, count_battles_today
        
        mock_battles = mock_mongodb_client['battles']
        mock_result = MagicMock()
        mock_result.inserted_id = "battle_id"
        mock_battles.insert_one.return_value = mock_result
        mock_battles.count_documents.return_value = 0
        
        with patch('services.database.operations.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.timezone = timezone
            
            # Test log_battle uses UTC
            log_battle("user1", "user2", "guild1")
            
            call_args = mock_battles.insert_one.call_args[0][0]
            assert call_args["timestamp"].tzinfo == timezone.utc
            
            # Test count_battles_today uses UTC for date calculation
            count_battles_today("user1", "user2", "guild1")
            
            # Verify datetime.now was called with timezone.utc
            mock_datetime.now.assert_called_with(timezone.utc)

    def test_battle_query_structure(self, mock_mongodb_client):
        """Test battle-related query structures are correct"""
        from services.database.operations import count_battles_today
        
        mock_battles = mock_mongodb_client['battles']
        mock_battles.count_documents.return_value = 2
        
        with patch('services.database.operations.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.timezone = timezone
            
            count_battles_today("user123", "user456", "guild789")
            
            # Check the query structure
            call_args = mock_battles.count_documents.call_args[0][0]
            
            assert "user_id" in call_args
            assert "opponent_id" in call_args
            assert "guild_id" in call_args
            assert "timestamp" in call_args
            assert "$gte" in call_args["timestamp"]

    def test_squib_game_active_states(self, mock_mongodb_client):
        """Test Squib Game active state query logic"""
        from services.database.operations import get_active_squib_game
        
        mock_sessions = mock_mongodb_client['sessions']
        mock_sessions.find_one.return_value = None
        
        get_active_squib_game("test_guild")
        
        call_args = mock_sessions.find_one.call_args[0][0]
        
        # Should query for both waiting_for_players and in_progress states
        assert "current_game_state" in call_args
        assert "$in" in call_args["current_game_state"]
        
        active_states = call_args["current_game_state"]["$in"]
        assert "waiting_for_players" in active_states
        assert "in_progress" in active_states
        assert len(active_states) == 2

    def test_pet_sorting_logic(self, mock_mongodb_client):
        """Test pet leaderboard sorting logic"""
        from services.database.operations import get_top_pets
        
        mock_pets = mock_mongodb_client['pets']
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value = []
        mock_pets.find.return_value = mock_cursor
        
        get_top_pets("test_guild", 15)
        
        # Check sorting parameters: level descending, then XP descending
        sort_args = mock_cursor.sort.call_args[0][0]
        assert sort_args == [("level", -1), ("xp", -1)]
        
        # Check limit
        mock_cursor.sort.return_value.limit.assert_called_once_with(15)

    def test_error_handling_patterns(self, mock_mongodb_client):
        """Test error handling in database operations"""
        from services.database.operations import update_pet, update_squib_game
        
        # Test operations return False when no documents are modified
        mock_pets = mock_mongodb_client['pets']
        mock_sessions = mock_mongodb_client['sessions']
        
        # Mock zero modified count
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_pets.update_one.return_value = mock_result
        mock_sessions.update_one.return_value = mock_result
        
        # Should return False for no modifications
        assert update_pet("fake_id", {}) is False
        assert update_squib_game("fake_id", {}) is False
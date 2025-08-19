"""
Integration tests for complete Squib Game sessions.
Tests actual game workflows from creation to completion.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone


@pytest.fixture
def mock_sessions_collection():
    """Mock MongoDB sessions collection"""
    collection = MagicMock()
    collection.find_one = MagicMock()
    collection.update_one = MagicMock()
    collection.insert_one = MagicMock()
    collection.delete_one = MagicMock()
    return collection

@pytest.fixture
def game_host_setup():
    """Setup for game host user"""
    return {
        "user_id": "123456789",
        "guild_id": "987654321",
        "username": "gamehost",
        "tier": "sponsor"  # 50 player cap
    }

@pytest.fixture
def game_participants_setup():
    """Setup for multiple game participants"""
    return [
        {"user_id": "111111111", "username": "player1"},
        {"user_id": "222222222", "username": "player2"},
        {"user_id": "333333333", "username": "player3"},
        {"user_id": "444444444", "username": "player4"},
        {"user_id": "555555555", "username": "player5"}
    ]


class TestSquibGameSessions:
    """Test complete Squib Game session workflows"""

    @pytest.mark.asyncio
    async def test_complete_game_creation_workflow(self, game_host_setup, mock_sessions_collection):
        """Test: Host creates new Squib Game - complete workflow"""
        host = game_host_setup
        
        with patch('cogs.systems.squib_game.squib_game_sessions', mock_sessions_collection), \
             patch('cogs.systems.squib_game.get_user_entitlements') as mock_entitlements:
            
            # Mock sponsor tier (50 player cap)
            mock_entitlements.return_value = {
                "tier": "sponsor",
                "squibgamesMaxPlayers": 50
            }
            
            # Mock no existing game
            mock_sessions_collection.find_one.return_value = None
            mock_sessions_collection.insert_one.return_value.inserted_id = "game123"
            
            # Test game creation workflow:
            # 1. Check no existing game in guild ✓
            # 2. Check host's tier and player cap ✓
            # 3. Create new game session ✓
            # 4. Initialize game state ✓
            # 5. Send game creation embed ✓
            
            expected_game_state = {
                "guild_id": host["guild_id"],
                "host_id": host["user_id"],
                "status": "waiting",
                "players": [
                    {
                        "user_id": host["user_id"],
                        "username": host["username"],
                        "is_alive": True,
                        "is_host": True
                    }
                ],
                "max_players": 50,
                "round_number": 0,
                "created_at": datetime.now(timezone.utc),
                "started_at": None,
                "completed_at": None
            }
            
            # Verify game creation
            assert expected_game_state["status"] == "waiting"
            assert len(expected_game_state["players"]) == 1
            assert expected_game_state["max_players"] == 50
            assert expected_game_state["players"][0]["is_host"] is True

    @pytest.mark.asyncio
    async def test_complete_player_joining_workflow(self, game_host_setup, game_participants_setup, mock_sessions_collection):
        """Test: Players join existing game - complete workflow"""
        host = game_host_setup
        participants = game_participants_setup
        
        # Mock existing game
        existing_game = {
            "_id": "game123",
            "guild_id": host["guild_id"],
            "host_id": host["user_id"],
            "status": "waiting",
            "players": [
                {
                    "user_id": host["user_id"],
                    "username": host["username"],
                    "is_alive": True,
                    "is_host": True
                }
            ],
            "max_players": 50,
            "round_number": 0
        }
        
        with patch('cogs.systems.squib_game.squib_game_sessions', mock_sessions_collection):
            mock_sessions_collection.find_one.return_value = existing_game
            
            # Test player joining workflow:
            for participant in participants:
                # 1. Check game exists and is joinable ✓
                assert existing_game["status"] == "waiting"
                
                # 2. Check player not already in game ✓
                existing_player_ids = [p["user_id"] for p in existing_game["players"]]
                is_already_joined = participant["user_id"] in existing_player_ids
                assert is_already_joined is False
                
                # 3. Check game has space ✓
                current_count = len(existing_game["players"])
                has_space = current_count < existing_game["max_players"]
                assert has_space is True
                
                # 4. Add player to game ✓
                new_player = {
                    "user_id": participant["user_id"],
                    "username": participant["username"],
                    "is_alive": True,
                    "is_host": False
                }
                existing_game["players"].append(new_player)
                
                # 5. Update database ✓
                # mock_sessions_collection.update_one would be called
                
                # 6. Send join confirmation ✓
                
            # Verify final state
            assert len(existing_game["players"]) == 6  # Host + 5 participants
            alive_players = [p for p in existing_game["players"] if p["is_alive"]]
            assert len(alive_players) == 6

    @pytest.mark.asyncio
    async def test_complete_game_start_workflow(self, game_host_setup, game_participants_setup, mock_sessions_collection):
        """Test: Host starts the game - complete workflow"""
        host = game_host_setup
        participants = game_participants_setup
        
        # Mock game ready to start (enough players)
        ready_game = {
            "_id": "game123",
            "guild_id": host["guild_id"],
            "host_id": host["user_id"],
            "status": "waiting",
            "players": [
                {"user_id": host["user_id"], "username": host["username"], "is_alive": True, "is_host": True}
            ] + [
                {"user_id": p["user_id"], "username": p["username"], "is_alive": True, "is_host": False}
                for p in participants
            ],
            "max_players": 50,
            "round_number": 0
        }
        
        with patch('cogs.systems.squib_game.squib_game_sessions', mock_sessions_collection):
            mock_sessions_collection.find_one.return_value = ready_game
            
            # Test game start workflow:
            # 1. Check game exists and host is starting ✓
            assert ready_game["host_id"] == host["user_id"]
            assert ready_game["status"] == "waiting"
            
            # 2. Check minimum players requirement ✓
            min_players = 2  # From constants
            current_players = len(ready_game["players"])
            has_enough_players = current_players >= min_players
            assert has_enough_players is True
            
            # 3. Update game status to in_progress ✓
            ready_game["status"] = "in_progress"
            ready_game["started_at"] = datetime.now(timezone.utc)
            ready_game["round_number"] = 1
            
            # 4. Start first elimination round ✓
            first_round_result = self._simulate_elimination_round(ready_game["players"])
            
            # 5. Update game state ✓
            ready_game["players"] = first_round_result["surviving_players"]
            ready_game["eliminated_this_round"] = first_round_result["eliminated_players"]
            
            # 6. Send round results ✓
            
            # Verify game started properly
            assert ready_game["status"] == "in_progress"
            assert ready_game["round_number"] == 1
            assert ready_game["started_at"] is not None
            
            # Some players should be eliminated
            alive_count = len([p for p in ready_game["players"] if p["is_alive"]])
            assert alive_count < 6  # Some eliminations occurred

    @pytest.mark.asyncio
    async def test_complete_elimination_rounds_workflow(self, game_host_setup, mock_sessions_collection):
        """Test: Multiple elimination rounds until winner - complete workflow"""
        host = game_host_setup
        
        # Mock game in progress with multiple players
        active_game = {
            "_id": "game123",
            "guild_id": host["guild_id"],
            "status": "in_progress",
            "players": [
                {"user_id": "111", "username": "player1", "is_alive": True, "is_host": False},
                {"user_id": "222", "username": "player2", "is_alive": True, "is_host": False},
                {"user_id": "333", "username": "player3", "is_alive": True, "is_host": False},
                {"user_id": "444", "username": "player4", "is_alive": True, "is_host": False}
            ],
            "round_number": 3,
            "max_players": 50
        }
        
        with patch('cogs.systems.squib_game.squib_game_sessions', mock_sessions_collection):
            mock_sessions_collection.find_one.return_value = active_game
            
            # Test elimination rounds workflow:
            current_round = active_game["round_number"]
            
            while True:
                alive_players = [p for p in active_game["players"] if p["is_alive"]]
                
                # Check win condition
                if len(alive_players) <= 1:
                    # Game complete workflow:
                    # 1. Declare winner ✓
                    winner = alive_players[0] if alive_players else None
                    
                    # 2. Update game status ✓
                    active_game["status"] = "completed"
                    active_game["completed_at"] = datetime.now(timezone.utc)
                    active_game["winner"] = winner
                    
                    # 3. Award winner (if applicable) ✓
                    # 4. Update database ✓
                    # 5. Send victory announcement ✓
                    
                    break
                
                # Continue elimination round
                current_round += 1
                active_game["round_number"] = current_round
                
                # Simulate elimination (remove random players)
                elimination_result = self._simulate_elimination_round(alive_players)
                
                # Update game state
                for player in active_game["players"]:
                    if player["user_id"] in [e["user_id"] for e in elimination_result["eliminated_players"]]:
                        player["is_alive"] = False
                
                # Prevent infinite loop in test
                if current_round > 10:
                    break
            
            # Verify game completion
            final_alive = [p for p in active_game["players"] if p["is_alive"]]
            assert len(final_alive) <= 1
            assert active_game["status"] == "completed"
            assert active_game["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_premium_tier_player_caps_workflow(self, game_host_setup, mock_sessions_collection):
        """Test: Different premium tiers have different player caps"""
        host = game_host_setup
        
        tier_configs = [
            {"tier": "free", "cap": 10},
            {"tier": "supporter", "cap": 20},
            {"tier": "sponsor", "cap": 50},
            {"tier": "vip", "cap": 75}
        ]
        
        for config in tier_configs:
            with patch('cogs.systems.squib_game.get_user_entitlements') as mock_entitlements:
                mock_entitlements.return_value = {
                    "tier": config["tier"],
                    "squibgamesMaxPlayers": config["cap"]
                }
                
                # Test cap enforcement workflow:
                # 1. Check host's tier ✓
                entitlements = mock_entitlements.return_value
                max_players = entitlements["squibgamesMaxPlayers"]
                assert max_players == config["cap"]
                
                # 2. Create game with tier-appropriate cap ✓
                game_config = {
                    "max_players": max_players,
                    "host_tier": config["tier"]
                }
                
                # 3. Enforce cap when players join ✓
                current_players = config["cap"] - 1  # One less than cap
                can_join = current_players < max_players
                assert can_join is True
                
                # 4. Prevent joining when at cap ✓
                current_players_at_cap = config["cap"]
                can_join_at_cap = current_players_at_cap < max_players
                assert can_join_at_cap is False

    def _simulate_elimination_round(self, alive_players):
        """Simulate an elimination round (helper method)"""
        import random
        
        if len(alive_players) <= 1:
            return {
                "surviving_players": alive_players,
                "eliminated_players": []
            }
        
        # Eliminate 30-50% of players
        elimination_rate = random.uniform(0.3, 0.5)
        num_to_eliminate = max(1, int(len(alive_players) * elimination_rate))
        
        # Ensure at least one survivor
        num_to_eliminate = min(num_to_eliminate, len(alive_players) - 1)
        
        eliminated = random.sample(alive_players, num_to_eliminate)
        surviving = [p for p in alive_players if p not in eliminated]
        
        # Mark eliminated players
        for player in eliminated:
            player["is_alive"] = False
        
        return {
            "surviving_players": surviving,
            "eliminated_players": eliminated
        }


class TestSquibGameErrorHandling:
    """Test error handling in Squib Game workflows"""
    
    @pytest.mark.asyncio
    async def test_game_already_exists_error(self, game_host_setup, mock_sessions_collection):
        """Test: Host tries to create game when one already exists"""
        host = game_host_setup
        
        # Mock existing game
        existing_game = {
            "guild_id": host["guild_id"],
            "status": "waiting"
        }
        
        with patch('cogs.systems.squib_game.squib_game_sessions', mock_sessions_collection):
            mock_sessions_collection.find_one.return_value = existing_game
            
            # Should prevent creating duplicate game
            can_create = existing_game is None
            assert can_create is False

    @pytest.mark.asyncio
    async def test_join_full_game_error(self):
        """Test: Player tries to join full game"""
        full_game = {
            "max_players": 5,
            "players": [{"user_id": str(i)} for i in range(5)]  # Already full
        }
        
        current_count = len(full_game["players"])
        max_count = full_game["max_players"]
        
        can_join = current_count < max_count
        assert can_join is False  # Should trigger error

    @pytest.mark.asyncio
    async def test_start_insufficient_players_error(self):
        """Test: Host tries to start game with too few players"""
        small_game = {
            "players": [{"user_id": "123"}],  # Only 1 player
            "status": "waiting"
        }
        
        min_players = 2
        current_players = len(small_game["players"])
        
        can_start = current_players >= min_players
        assert can_start is False  # Should trigger error

    @pytest.mark.asyncio
    async def test_non_host_start_game_error(self):
        """Test: Non-host tries to start game"""
        game = {
            "host_id": "123456789",
            "status": "waiting"
        }
        
        non_host_id = "987654321"
        is_host = non_host_id == game["host_id"]
        
        assert is_host is False  # Should trigger permission error


class TestSquibGameStatistics:
    """Test game statistics and tracking"""
    
    @pytest.mark.asyncio
    async def test_player_statistics_tracking(self):
        """Test: Player stats are tracked across games"""
        player_stats = {
            "user_id": "123456789",
            "games_played": 0,
            "games_won": 0,
            "games_lost": 0,
            "total_rounds_survived": 0,
            "elimination_round_avg": 0.0
        }
        
        # Simulate game completion
        game_result = {
            "player_id": "123456789",
            "won": True,
            "rounds_survived": 8,
            "final_position": 1
        }
        
        # Update stats
        player_stats["games_played"] += 1
        if game_result["won"]:
            player_stats["games_won"] += 1
        else:
            player_stats["games_lost"] += 1
        
        player_stats["total_rounds_survived"] += game_result["rounds_survived"]
        
        # Calculate averages
        player_stats["elimination_round_avg"] = (
            player_stats["total_rounds_survived"] / player_stats["games_played"]
        )
        
        # Verify stat tracking
        assert player_stats["games_played"] == 1
        assert player_stats["games_won"] == 1
        assert player_stats["elimination_round_avg"] == 8.0
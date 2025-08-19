import pytest
from datetime import datetime, timezone
from typing import Any


class TestDatabaseModels:
    """Test database model structures and functionality"""
    
    def test_active_item_creation(self):
        """Test ActiveItem dataclass creation and attributes"""
        from services.database.models import ActiveItem
        
        item = ActiveItem(
            item_id="strength_potion_1",
            name="Strength Potion",
            stat="strength",
            value=5,
            battles_remaining=3
        )
        
        assert item.item_id == "strength_potion_1"
        assert item.name == "Strength Potion"
        assert item.stat == "strength"
        assert item.value == 5
        assert item.battles_remaining == 3

    def test_active_item_stat_types(self):
        """Test ActiveItem supports different stat types"""
        from services.database.models import ActiveItem
        
        # Test different stat types
        stat_types = ["strength", "defense", "health", "speed", "luck"]
        
        for stat_type in stat_types:
            item = ActiveItem(
                item_id=f"{stat_type}_buff",
                name=f"{stat_type.title()} Buff",
                stat=stat_type,
                value=10,
                battles_remaining=5
            )
            assert item.stat == stat_type

    def test_pet_quest_creation(self):
        """Test PetQuest dataclass creation and default values"""
        from services.database.models import PetQuest
        
        quest = PetQuest(
            id=1,
            description="Win 5 battles",
            progress_required=5,
            xp_reward=100,
            cash_reward=50
        )
        
        assert quest.id == 1
        assert quest.description == "Win 5 battles"
        assert quest.progress_required == 5
        assert quest.xp_reward == 100
        assert quest.cash_reward == 50
        assert quest.progress == 0  # Default value
        assert quest.completed is False  # Default value

    def test_pet_quest_progress_tracking(self):
        """Test PetQuest progress and completion tracking"""
        from services.database.models import PetQuest
        
        quest = PetQuest(
            id=2,
            description="Deal 1000 damage",
            progress_required=1000,
            xp_reward=200,
            cash_reward=100,
            progress=750
        )
        
        # Test partial progress
        assert quest.progress == 750
        assert quest.completed is False
        
        # Test completion
        quest.progress = 1000
        quest.completed = True
        assert quest.progress >= quest.progress_required
        assert quest.completed is True

    def test_pet_achievement_creation(self):
        """Test PetAchievement dataclass creation"""
        from services.database.models import PetAchievement
        
        achievement = PetAchievement(
            id=10,
            description="Reach level 50",
            progress_required=50,
            xp_reward=1000,
            cash_reward=500
        )
        
        assert achievement.id == 10
        assert achievement.description == "Reach level 50"
        assert achievement.progress_required == 50
        assert achievement.xp_reward == 1000
        assert achievement.cash_reward == 500
        assert achievement.progress == 0
        assert achievement.completed is False

    def test_pet_creation_with_defaults(self):
        """Test Pet dataclass creation with default values"""
        from services.database.models import Pet
        
        pet = Pet(
            user_id="123456789",
            guild_id="987654321",
            name="Fluffy",
            icon="🐱",
            color=0xFF5733
        )
        
        # Check required fields
        assert pet.user_id == "123456789"
        assert pet.guild_id == "987654321"
        assert pet.name == "Fluffy"
        assert pet.icon == "🐱"
        assert pet.color == 0xFF5733
        
        # Check default values
        assert pet.level == 1
        assert pet.xp == 0
        assert pet.strength == 10
        assert pet.defense == 10
        assert pet.health == 100
        assert pet.balance == 0
        assert pet.killstreak == 0
        assert pet.loss_streak == 0
        assert pet.daily_quests == []
        assert pet.achievements == []
        assert pet.active_items == []
        assert pet.last_vote_reward_time is None
        assert pet.claimed_daily_completion_bonus is False
        assert pet._id is None

    def test_pet_with_custom_stats(self):
        """Test Pet creation with custom stat values"""
        from services.database.models import Pet, PetQuest, ActiveItem
        
        quest = PetQuest(
            id=1,
            description="Test quest",
            progress_required=10,
            xp_reward=50,
            cash_reward=25
        )
        
        item = ActiveItem(
            item_id="test_item",
            name="Test Item",
            stat="strength",
            value=5,
            battles_remaining=3
        )
        
        pet = Pet(
            user_id="123456789",
            guild_id="987654321",
            name="Warrior Cat",
            icon="⚔️",
            color=0x000000,
            level=25,
            xp=15000,
            strength=50,
            defense=40,
            health=200,
            balance=1000,
            killstreak=10,
            loss_streak=2,
            daily_quests=[quest],
            active_items=[item]
        )
        
        assert pet.level == 25
        assert pet.xp == 15000
        assert pet.strength == 50
        assert pet.defense == 40
        assert pet.health == 200
        assert pet.balance == 1000
        assert pet.killstreak == 10
        assert pet.loss_streak == 2
        assert len(pet.daily_quests) == 1
        assert len(pet.active_items) == 1
        assert pet.daily_quests[0].description == "Test quest"
        assert pet.active_items[0].name == "Test Item"

    def test_battle_log_creation(self):
        """Test BattleLog dataclass creation"""
        from services.database.models import BattleLog
        
        timestamp = datetime.now(timezone.utc)
        battle_log = BattleLog(
            user_id="123456789",
            opponent_id="987654321",
            guild_id="555666777",
            timestamp=timestamp
        )
        
        assert battle_log.user_id == "123456789"
        assert battle_log.opponent_id == "987654321"
        assert battle_log.guild_id == "555666777"
        assert battle_log.timestamp == timestamp
        assert battle_log._id is None

    def test_squib_game_participant_creation(self):
        """Test SquibGameParticipant dataclass creation"""
        from services.database.models import SquibGameParticipant
        
        participant = SquibGameParticipant(
            user_id="123456789",
            username="TestUser"
        )
        
        assert participant.user_id == "123456789"
        assert participant.username == "TestUser"
        assert participant.status == "alive"  # Default value

    def test_squib_game_participant_status_changes(self):
        """Test SquibGameParticipant status modifications"""
        from services.database.models import SquibGameParticipant
        
        participant = SquibGameParticipant(
            user_id="123456789",
            username="TestUser",
            status="eliminated"
        )
        
        assert participant.status == "eliminated"
        
        # Test status change
        participant.status = "winner"
        assert participant.status == "winner"

    def test_squib_game_session_creation(self):
        """Test SquibGameSession dataclass creation with defaults"""
        from services.database.models import SquibGameSession, SquibGameParticipant
        
        participant1 = SquibGameParticipant(user_id="111", username="Player1")
        participant2 = SquibGameParticipant(user_id="222", username="Player2")
        
        session = SquibGameSession(
            guild_id="987654321",
            host_user_id="123456789",
            session_id="game_123",
            participants=[participant1, participant2]
        )
        
        assert session.guild_id == "987654321"
        assert session.host_user_id == "123456789"
        assert session.session_id == "game_123"
        assert session.current_round == 0  # Default
        assert session.current_game_state == "waiting_for_players"  # Default
        assert len(session.participants) == 2
        assert isinstance(session.created_at, datetime)
        assert session._id is None

    def test_squib_game_session_state_transitions(self):
        """Test SquibGameSession state management"""
        from services.database.models import SquibGameSession
        
        session = SquibGameSession(
            guild_id="987654321",
            host_user_id="123456789",
            session_id="game_456"
        )
        
        # Test state transitions
        valid_states = ["waiting_for_players", "in_progress", "completed", "cancelled"]
        
        for state in valid_states:
            session.current_game_state = state
            assert session.current_game_state == state

    def test_squib_game_session_round_progression(self):
        """Test SquibGameSession round management"""
        from services.database.models import SquibGameSession
        
        session = SquibGameSession(
            guild_id="987654321",
            host_user_id="123456789",
            session_id="game_789"
        )
        
        # Test round progression
        assert session.current_round == 0
        
        session.current_round = 1
        assert session.current_round == 1
        
        session.current_round = 10
        assert session.current_round == 10

    def test_squib_game_stats_creation(self):
        """Test SquibGameStats dataclass creation"""
        from services.database.models import SquibGameStats
        
        stats = SquibGameStats(
            user_id="123456789",
            guild_id="987654321"
        )
        
        assert stats.user_id == "123456789"
        assert stats.guild_id == "987654321"
        assert stats.wins == 0  # Default
        assert stats.games_played == 0  # Default
        assert stats._id is None

    def test_squib_game_stats_with_values(self):
        """Test SquibGameStats with custom values"""
        from services.database.models import SquibGameStats
        
        stats = SquibGameStats(
            user_id="123456789",
            guild_id="987654321",
            wins=15,
            games_played=50
        )
        
        assert stats.wins == 15
        assert stats.games_played == 50
        
        # Test win rate calculation (not in model but useful for testing)
        win_rate = (stats.wins / stats.games_played) * 100 if stats.games_played > 0 else 0
        assert win_rate == 30.0

    def test_pet_quest_reward_types(self):
        """Test PetQuest supports different reward types"""
        from services.database.models import PetQuest
        
        # High XP, low cash quest
        xp_quest = PetQuest(
            id=1,
            description="Training quest",
            progress_required=10,
            xp_reward=500,
            cash_reward=10
        )
        
        # High cash, low XP quest
        cash_quest = PetQuest(
            id=2,
            description="Treasure hunt",
            progress_required=5,
            xp_reward=50,
            cash_reward=200
        )
        
        # Balanced quest
        balanced_quest = PetQuest(
            id=3,
            description="Balanced quest",
            progress_required=15,
            xp_reward=100,
            cash_reward=100
        )
        
        assert xp_quest.xp_reward > xp_quest.cash_reward
        assert cash_quest.cash_reward > cash_quest.xp_reward
        assert balanced_quest.xp_reward == balanced_quest.cash_reward

    def test_active_item_battle_countdown(self):
        """Test ActiveItem battle countdown functionality"""
        from services.database.models import ActiveItem
        
        item = ActiveItem(
            item_id="temp_buff",
            name="Temporary Buff",
            stat="strength",
            value=10,
            battles_remaining=5
        )
        
        # Simulate battle usage
        original_battles = item.battles_remaining
        item.battles_remaining -= 1
        
        assert item.battles_remaining == original_battles - 1
        assert item.battles_remaining == 4
        
        # Test expiration
        item.battles_remaining = 0
        assert item.battles_remaining == 0

    def test_pet_id_handling(self):
        """Test Pet _id field for MongoDB ObjectId compatibility"""
        from services.database.models import Pet
        
        pet = Pet(
            user_id="123456789",
            guild_id="987654321",
            name="Test Pet",
            icon="🐱",
            color=0x000000
        )
        
        # Initially None
        assert pet._id is None
        
        # Can be set to any type (for ObjectId compatibility)
        pet._id = "507f1f77bcf86cd799439011"  # String ObjectId
        assert pet._id == "507f1f77bcf86cd799439011"
        
        # Can also handle actual ObjectId-like objects
        class MockObjectId:
            def __str__(self):
                return "mock_object_id"
        
        mock_id = MockObjectId()
        pet._id = mock_id
        assert pet._id == mock_id

    def test_model_field_types(self):
        """Test model field type consistency"""
        from services.database.models import Pet, BattleLog, SquibGameSession
        
        # Test string fields
        pet = Pet(
            user_id="123456789",
            guild_id="987654321", 
            name="Test",
            icon="🐱",
            color=0x000000
        )
        
        assert isinstance(pet.user_id, str)
        assert isinstance(pet.guild_id, str)
        assert isinstance(pet.name, str)
        assert isinstance(pet.icon, str)
        
        # Test integer fields
        assert isinstance(pet.level, int)
        assert isinstance(pet.xp, int)
        assert isinstance(pet.color, int)
        
        # Test datetime fields
        battle_log = BattleLog(
            user_id="123",
            opponent_id="456", 
            guild_id="789",
            timestamp=datetime.now(timezone.utc)
        )
        
        assert isinstance(battle_log.timestamp, datetime)
        
        # Test automatic datetime field
        session = SquibGameSession(
            guild_id="123",
            host_user_id="456",
            session_id="789"
        )
        
        assert isinstance(session.created_at, datetime)

    def test_pet_balance_tracking(self):
        """Test Pet balance field for cash management"""
        from services.database.models import Pet
        
        pet = Pet(
            user_id="123456789",
            guild_id="987654321",
            name="Rich Cat",
            icon="💰",
            color=0xFFD700,
            balance=1500
        )
        
        assert pet.balance == 1500
        
        # Test balance operations
        pet.balance += 500  # Earnings
        assert pet.balance == 2000
        
        pet.balance -= 300  # Purchase
        assert pet.balance == 1700
        
        # Test negative balance (debt)
        pet.balance = -100
        assert pet.balance == -100

    def test_pet_streak_tracking(self):
        """Test Pet killstreak and loss_streak fields"""
        from services.database.models import Pet
        
        pet = Pet(
            user_id="123456789",
            guild_id="987654321",
            name="Streak Cat",
            icon="🔥",
            color=0xFF0000
        )
        
        # Test killstreak
        pet.killstreak = 10
        pet.loss_streak = 0
        assert pet.killstreak == 10
        assert pet.loss_streak == 0
        
        # Test loss streak (killstreak should reset)
        pet.killstreak = 0
        pet.loss_streak = 5
        assert pet.killstreak == 0
        assert pet.loss_streak == 5

    def test_datetime_timezone_awareness(self):
        """Test datetime fields use UTC timezone"""
        from services.database.models import BattleLog, SquibGameSession
        
        utc_time = datetime.now(timezone.utc)
        
        battle_log = BattleLog(
            user_id="123",
            opponent_id="456",
            guild_id="789", 
            timestamp=utc_time
        )
        
        assert battle_log.timestamp.tzinfo == timezone.utc
        
        # Test SquibGameSession auto-generated timestamp
        session = SquibGameSession(
            guild_id="123",
            host_user_id="456",
            session_id="789"
        )
        
        assert session.created_at.tzinfo == timezone.utc
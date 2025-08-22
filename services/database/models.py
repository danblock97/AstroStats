# services/database/models.py
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
import datetime

# Structure for active items/buffs
@dataclass
class ActiveItem:
    item_id: str
    name: str
    stat: str # e.g., 'strength', 'defense', 'health'
    value: int # The amount of buff
    battles_remaining: int # How many battles the buff lasts

@dataclass
class PetQuest:
    id: int
    description: str
    progress_required: int
    xp_reward: int
    cash_reward: int # Added cash reward
    progress: int = 0
    completed: bool = False


@dataclass
class PetAchievement:
    id: int
    description: str
    progress_required: int
    xp_reward: int
    cash_reward: int # Added cash reward
    progress: int = 0
    completed: bool = False


@dataclass
class Pet:
    user_id: str
    guild_id: str
    name: str
    icon: str
    color: int
    level: int = 1
    xp: int = 0
    strength: int = 10
    defense: int = 10
    health: int = 100
    balance: int = 0 # Added balance field
    killstreak: int = 0
    loss_streak: int = 0
    daily_quests: List[PetQuest] = field(default_factory=list)
    achievements: List[PetAchievement] = field(default_factory=list)
    active_items: List[ActiveItem] = field(default_factory=list) # Added active items/buffs
    last_vote_reward_time: Optional[str] = None
    claimed_daily_completion_bonus: bool = False # Track if daily bonus was claimed
    _id: Optional[Any] = None # Use Any for ObjectId compatibility

@dataclass
class BattleLog:
    user_id: str
    opponent_id: str
    guild_id: str
    timestamp: datetime.datetime
    _id: Optional[Any] = None # Use Any for ObjectId compatibility

@dataclass
class SquibGameParticipant:
    user_id: str
    username: str
    status: str = "alive"

@dataclass
class SquibGameSession:
    guild_id: str
    host_user_id: str
    session_id: str
    current_round: int = 0
    current_game_state: str = "waiting_for_players"
    participants: List[SquibGameParticipant] = field(default_factory=list)
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    _id: Optional[Any] = None # Use Any for ObjectId compatibility

@dataclass
class SquibGameStats:
    user_id: str
    guild_id: str
    wins: int = 0
    games_played: int = 0
    _id: Optional[Any] = None # Use Any for ObjectId compatibility

@dataclass
class WelcomeSettings:
    guild_id: str
    enabled: bool = False
    custom_message: Optional[str] = None
    custom_image_data: Optional[str] = None  # Base64 encoded image data
    custom_image_filename: Optional[str] = None  # Original filename for reference
    _id: Optional[Any] = None # Use Any for ObjectId compatibility


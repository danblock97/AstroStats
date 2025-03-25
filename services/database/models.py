from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
import datetime

@dataclass
class PetQuest:
    id: int
    description: str
    progress_required: int
    progress: int = 0
    completed: bool = False
    xp_reward: int = 0

@dataclass
class PetAchievement:
    id: int
    description: str
    progress_required: int
    progress: int = 0
    completed: bool = False
    xp_reward: int = 0

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
    killstreak: int = 0
    loss_streak: int = 0
    daily_quests: List[PetQuest] = field(default_factory=list)
    achievements: List[PetAchievement] = field(default_factory=list)
    last_vote_reward_time: Optional[str] = None
    _id: Optional[str] = None

@dataclass
class BattleLog:
    user_id: str
    opponent_id: str
    guild_id: str
    timestamp: datetime.datetime
    _id: Optional[str] = None

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
    _id: Optional[str] = None

@dataclass
class SquibGameStats:
    user_id: str
    guild_id: str
    wins: int = 0
    games_played: int = 0
    _id: Optional[str] = None
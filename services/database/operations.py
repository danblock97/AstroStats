import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from pymongo import MongoClient

from config.settings import MONGODB_URI

logger = logging.getLogger(__name__)

# Initialize MongoDB client
client = MongoClient(MONGODB_URI)
db = client['astrostats_database']

# Collections
pets_collection = db['pets']
battle_logs_collection = db['battle_logs']
squib_game_sessions = db['squib_game_sessions']
squib_game_stats = db['squib_game_stats']

# Pet Operations
def get_pet(user_id: str, guild_id: str) -> Optional[Dict[str, Any]]:
    """Get a pet by user ID and guild ID."""
    return pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})

def create_pet(pet_data: Dict[str, Any]) -> str:
    """Create a new pet and return its ID."""
    result = pets_collection.insert_one(pet_data)
    return str(result.inserted_id)

def update_pet(pet_id: str, update_data: Dict[str, Any]) -> bool:
    """Update a pet by ID."""
    result = pets_collection.update_one({"_id": pet_id}, {"$set": update_data})
    return result.modified_count > 0

def get_top_pets(guild_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get the top pets by level and XP."""
    return list(pets_collection.find({"guild_id": guild_id}).sort([("level", -1), ("xp", -1)]).limit(limit))

# Battle Log Operations
def log_battle(user_id: str, opponent_id: str, guild_id: str) -> str:
    """Log a battle between two users."""
    battle_data = {
        "user_id": user_id,
        "opponent_id": opponent_id,
        "guild_id": guild_id,
        "timestamp": datetime.now(timezone.utc)
    }
    result = battle_logs_collection.insert_one(battle_data)
    return str(result.inserted_id)

def count_battles_today(user_id: str, opponent_id: str, guild_id: str) -> int:
    """Count battles between two users today."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return battle_logs_collection.count_documents({
        "user_id": user_id,
        "opponent_id": opponent_id,
        "guild_id": guild_id,
        "timestamp": {"$gte": today}
    })

# Squib Game Operations
def create_squib_game_session(session_data: Dict[str, Any]) -> str:
    """Create a new Squib Game session."""
    result = squib_game_sessions.insert_one(session_data)
    return str(result.inserted_id)

def get_active_squib_game(guild_id: str) -> Optional[Dict[str, Any]]:
    """Get the active Squib Game session for a guild."""
    return squib_game_sessions.find_one({
        "guild_id": guild_id,
        "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
    })

def update_squib_game(game_id: str, update_data: Dict[str, Any]) -> bool:
    """Update a Squib Game session."""
    result = squib_game_sessions.update_one({"_id": game_id}, {"$set": update_data})
    return result.modified_count > 0

def update_squib_game_stats(user_id: str, guild_id: str, win_increment: int = 0) -> int:
    """Update a user's Squib Game stats and return their win count."""
    user_stats = squib_game_stats.find_one({"user_id": user_id, "guild_id": guild_id})
    if not user_stats:
        new_stats = {
            "user_id": user_id,
            "guild_id": guild_id,
            "wins": win_increment,
            "games_played": 1
        }
        squib_game_stats.insert_one(new_stats)
        return new_stats["wins"]
    else:
        new_wins = user_stats.get("wins", 0) + win_increment
        new_games_played = user_stats.get("games_played", 0) + 1
        squib_game_stats.update_one(
            {"_id": user_stats["_id"]},
            {"$set": {"wins": new_wins, "games_played": new_games_played}}
        )
        return new_wins
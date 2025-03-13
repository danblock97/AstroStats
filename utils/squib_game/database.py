import os
from pymongo import MongoClient

mongo_client = MongoClient(os.getenv('MONGODB_URI'))
db = mongo_client['astrostats_database']
squib_game_sessions = db['squib_game_sessions']
squib_game_stats = db['squib_game_stats']

def update_squib_game_stats(user_id: str, guild_id: str, win_increment: int = 0) -> int:
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

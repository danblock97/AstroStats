import random
from pymongo import MongoClient
import os
from utils.pets.petconstants import DAILY_QUESTS, ACHIEVEMENTS

# Initialize the database connection (if not already managed elsewhere)
mongo_client = MongoClient(os.getenv('MONGODB_URI'))
db = mongo_client['astrostats_database']
pets_collection = db['pets']

def assign_daily_quests(pet: dict) -> dict:
    random_daily_quests = random.sample(DAILY_QUESTS, 3)
    pet_daily_quests = []
    for quest in random_daily_quests:
        pet_daily_quests.append({
            "id": quest["id"],
            "description": quest["description"],
            "progress_required": quest["progress_required"],
            "progress": 0,
            "completed": False,
            "xp_reward": quest["xp_reward"]
        })
    pet['daily_quests'] = pet_daily_quests
    if pet.get('_id') is not None:
        pets_collection.update_one({"_id": pet["_id"]}, {"$set": {"daily_quests": pet_daily_quests}})
    return pet

def assign_achievements(pet: dict) -> dict:
    pet_achievements = []
    for achievement in ACHIEVEMENTS:
        pet_achievements.append({
            "id": achievement["id"],
            "description": achievement["description"],
            "progress_required": achievement["progress_required"],
            "progress": 0,
            "completed": False,
            "xp_reward": achievement["xp_reward"]
        })
    pet['achievements'] = pet_achievements
    if pet.get('_id') is not None:
        pets_collection.update_one({"_id": pet["_id"]}, {"$set": {"achievements": pet_achievements}})
    return pet

def ensure_quests_and_achievements(pet: dict) -> dict:
    if 'daily_quests' not in pet or not pet['daily_quests']:
        pet = assign_daily_quests(pet)
    if 'achievements' not in pet or not pet['achievements']:
        pet = assign_achievements(pet)
    return pet

def update_quests_and_achievements(pet: dict, battle_stats: dict):
    completed_quests = []
    completed_achievements = []
    
    for quest in pet['daily_quests']:
        if quest['completed']:
            continue
        if "Win " in quest['description']:
            quest['progress'] += battle_stats.get('battles_won', 0)
        elif "battle win streak" in quest['description']:
            if pet.get('killstreak', 0) >= quest['progress_required']:
                quest['progress'] = quest['progress_required']
        elif "battle killstreak" in quest['description']:
            if pet.get('killstreak', 0) >= quest['progress_required']:
                quest['progress'] = quest['progress_required']
        elif "Inflict" in quest['description'] and "critical hits" in quest['description']:
            quest['progress'] += battle_stats.get('critical_hits', 0)
        elif "Land" in quest['description'] and "lucky hits" in quest['description']:
            quest['progress'] += battle_stats.get('lucky_hits', 0)
        elif "Lose" in quest['description']:
            quest['progress'] += battle_stats.get('battles_lost', 0)
        elif "Earn" in quest['description'] and "XP from battles" in quest['description']:
            quest['progress'] += battle_stats.get('xp_earned', 0)
        elif "Participate in" in quest['description'] and "battles" in quest['description']:
            quest['progress'] += 1
        elif "Deal" in quest['description'] and "damage in total" in quest['description']:
            quest['progress'] += battle_stats.get('damage_dealt', 0)
    
        if quest['progress'] >= quest['progress_required']:
            quest['progress'] = quest['progress_required']
            quest['completed'] = True
            pet['xp'] += quest['xp_reward']
            completed_quests.append(quest)
    
    for achievement in pet['achievements']:
        if achievement['completed']:
            continue
        if "Win " in achievement['description']:
            achievement['progress'] += battle_stats.get('battles_won', 0)
        elif "battle killstreak" in achievement['description']:
            if pet.get('killstreak', 0) >= achievement['progress_required']:
                achievement['progress'] = achievement['progress_required']
        elif "Deal" in achievement['description'] and "total damage" in achievement['description']:
            achievement['progress'] += battle_stats.get('damage_dealt', 0)
        elif "Land" in achievement['description'] and "critical hits" in achievement['description']:
            achievement['progress'] += battle_stats.get('critical_hits', 0)
        elif "Land" in achievement['description'] and "lucky hits" in achievement['description']:
            achievement['progress'] += battle_stats.get('lucky_hits', 0)
    
        if achievement['progress'] >= achievement['progress_required']:
            achievement['progress'] = achievement['progress_required']
            achievement['completed'] = True
            pet['xp'] += achievement['xp_reward']
            completed_achievements.append(achievement)
    
    return completed_quests, completed_achievements

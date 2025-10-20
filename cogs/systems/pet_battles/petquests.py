# cogs/systems/pet_battles/petquests.py
import random
import logging
from typing import List, Tuple, Dict, Any
from bson import ObjectId  # Import ObjectId

from .petconstants import DAILY_QUESTS, ACHIEVEMENTS, DAILY_COMPLETION_BONUS
from services.database import get_mongo_client
from services.premium import get_user_entitlements

# Initialize the database connection
mongo_client = get_mongo_client()
db = mongo_client['astrostats_database']
pets_collection = db['pets']

logger = logging.getLogger(__name__)

def assign_daily_quests(pet: Dict[str, Any]) -> Dict[str, Any]:
    """Assigns random daily quests to a pet. Base 3 plus premium bonus."""
    try:
        user_id = str(pet.get('user_id', ''))
        ent = get_user_entitlements(user_id) if user_id else {"dailyPetQuestsBonus": 0}
        num_quests = 3 + int(ent.get('dailyPetQuestsBonus', 0))
    except Exception:
        num_quests = 3
    num_quests = max(1, min(len(DAILY_QUESTS), num_quests))
    random_daily_quests = random.sample(DAILY_QUESTS, num_quests)
    pet_daily_quests = []
    for quest in random_daily_quests:
        pet_daily_quests.append({
            "id": quest["id"],
            "description": quest["description"],
            "progress_required": quest["progress_required"],
            "progress": 0,
            "completed": False,
            "xp_reward": quest["xp_reward"],
            "cash_reward": quest["cash_reward"] # Include cash reward
        })
    pet['daily_quests'] = pet_daily_quests
    pet['claimed_daily_completion_bonus'] = False # Reset bonus claim status
    # Ensure _id is ObjectId if present
    pet_id = pet.get('_id')
    if pet_id is not None and not isinstance(pet_id, ObjectId):
        try:
            pet_id = ObjectId(pet_id)
        except Exception:
            logger.error(f"Could not convert pet_id {pet_id} to ObjectId for daily quest update.")
            pet_id = None # Avoid updating if ID is invalid

    if pet_id is not None:
        pets_collection.update_one(
            {"_id": pet_id, "is_locked": {"$ne": True}},
            {"$set": {"daily_quests": pet_daily_quests, "claimed_daily_completion_bonus": False}}
        )
    return pet


def assign_achievements(pet: Dict[str, Any]) -> Dict[str, Any]:
    """Assigns all achievements to a pet if they don't exist."""
    pet_achievements = []
    for achievement in ACHIEVEMENTS:
        pet_achievements.append({
            "id": achievement["id"],
            "description": achievement["description"],
            "progress_required": achievement["progress_required"],
            "progress": 0,
            "completed": False,
            "xp_reward": achievement["xp_reward"],
            "cash_reward": achievement["cash_reward"] # Include cash reward
        })
    pet['achievements'] = pet_achievements
    # Ensure _id is ObjectId if present
    pet_id = pet.get('_id')
    if pet_id is not None and not isinstance(pet_id, ObjectId):
        try:
            pet_id = ObjectId(pet_id)
        except Exception:
            logger.error(f"Could not convert pet_id {pet_id} to ObjectId for achievement update.")
            pet_id = None # Avoid updating if ID is invalid

    if pet_id is not None:
        pets_collection.update_one({"_id": pet_id, "is_locked": {"$ne": True}}, {"$set": {"achievements": pet_achievements}})
    return pet


def ensure_quests_and_achievements(pet: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures a pet has both daily quests and achievements assigned."""
    updated = False
    if 'daily_quests' not in pet or not pet['daily_quests']:
        pet = assign_daily_quests(pet)
        updated = True
    else:
        # Top-up daily quests if current entitlements allow more than currently assigned
        try:
            if not pet.get('is_locked'):
                ent = get_user_entitlements(str(pet.get('user_id', '')))
                desired = 3 + int(ent.get('dailyPetQuestsBonus', 0) or 0)
                desired = max(1, min(len(DAILY_QUESTS), desired))
                current = len(pet.get('daily_quests', []))
                if current < desired:
                    # Add additional unique quests
                    existing_ids = {q.get('id') for q in pet['daily_quests']}
                    candidates = [q for q in DAILY_QUESTS if q['id'] not in existing_ids]
                    to_add = desired - current
                    if candidates and to_add > 0:
                        for quest in random.sample(candidates, min(len(candidates), to_add)):
                            pet['daily_quests'].append({
                                "id": quest["id"],
                                "description": quest["description"],
                                "progress_required": quest["progress_required"],
                                "progress": 0,
                                "completed": False,
                                "xp_reward": quest["xp_reward"],
                                "cash_reward": quest["cash_reward"]
                            })
                        updated = True
        except Exception:
            pass
    if 'achievements' not in pet or not pet['achievements']:
        pet = assign_achievements(pet)
        updated = True
    # Add missing fields if they don't exist (for backward compatibility)
    if 'balance' not in pet:
        pet['balance'] = 0
        updated = True
    if 'active_items' not in pet:
        pet['active_items'] = []
        updated = True
    if 'claimed_daily_completion_bonus' not in pet:
        pet['claimed_daily_completion_bonus'] = False
        updated = True

    # Save if any updates were made during ensure step
    if updated:
         # Ensure _id is ObjectId if present
        pet_id = pet.get('_id')
        if pet_id is not None and not isinstance(pet_id, ObjectId):
            try:
                pet_id = ObjectId(pet_id)
            except Exception:
                 logger.error(f"Could not convert pet_id {pet_id} to ObjectId during ensure.")
                 pet_id = None

        if pet_id is not None:
            update_fields = {
                "daily_quests": pet['daily_quests'],
                "achievements": pet['achievements'],
                "balance": pet['balance'],
                "active_items": pet['active_items'],
                "claimed_daily_completion_bonus": pet['claimed_daily_completion_bonus']
            }
            pets_collection.update_one({"_id": pet_id}, {"$set": update_fields})

    return pet


def update_quests_and_achievements(pet: Dict[str, Any], battle_stats: Dict[str, Any]) -> Tuple[List[Dict], List[Dict], bool]:
    """
    Updates quest and achievement progress based on battle stats.
    Awards XP and cash upon completion.
    Checks for daily completion bonus.
    Returns lists of completed quests, completed achievements, and if the daily bonus was awarded.
    """
    completed_quests_this_update = []
    completed_achievements_this_update = []
    daily_bonus_awarded = False

    # --- Update Daily Quests ---
    all_daily_quests_completed_before = all(q.get('completed', False) for q in pet.get('daily_quests', []))

    for quest in pet.get('daily_quests', []):
        if quest.get('completed', False):
            continue

        initial_progress = quest.get('progress', 0)

        # Update progress based on quest description and battle stats
        if "Win " in quest['description']:
            quest['progress'] = min(quest['progress_required'], initial_progress + battle_stats.get('battles_won', 0))
        elif "battle win streak" in quest['description']:
             # Check current killstreak against required progress directly
            if pet.get('killstreak', 0) >= quest['progress_required']:
                 quest['progress'] = quest['progress_required']
            # No else needed, progress stays as is if streak not met
        elif "battle killstreak" in quest['description']:
            # Check current killstreak against required progress directly
            if pet.get('killstreak', 0) >= quest['progress_required']:
                quest['progress'] = quest['progress_required']
        elif "Inflict" in quest['description'] and "critical hits" in quest['description']:
            quest['progress'] = min(quest['progress_required'], initial_progress + battle_stats.get('critical_hits', 0))
        elif "Land" in quest['description'] and "lucky hits" in quest['description']:
            quest['progress'] = min(quest['progress_required'], initial_progress + battle_stats.get('lucky_hits', 0))
        elif "Lose" in quest['description']:
            quest['progress'] = min(quest['progress_required'], initial_progress + battle_stats.get('battles_lost', 0))
        elif "Earn" in quest['description'] and "XP from battles" in quest['description']:
            quest['progress'] = min(quest['progress_required'], initial_progress + battle_stats.get('xp_earned', 0))
        elif "Participate in" in quest['description'] and "battles" in quest['description']:
            quest['progress'] = min(quest['progress_required'], initial_progress + 1) # Increment by 1 per battle
        elif "Deal" in quest['description'] and "damage in total" in quest['description']:
            quest['progress'] = min(quest['progress_required'], initial_progress + battle_stats.get('damage_dealt', 0))

        # Check for completion
        if quest['progress'] >= quest['progress_required'] and not quest.get('completed', False):
            quest['completed'] = True
            # Apply XP multiplier by tier
            try:
                ent = get_user_entitlements(str(pet.get('user_id','')))
                tier = ent.get('tier','free')
                mult = 1.0
                if tier == 'supporter':
                    mult = 1.2
                elif tier == 'sponsor':
                    mult = 1.5
                elif tier == 'vip':
                    mult = 1.75
                pet['xp'] += int(round(quest.get('xp_reward', 0) * mult))
            except Exception:
                pet['xp'] += quest.get('xp_reward', 0)
            try:
                ent = get_user_entitlements(str(pet.get('user_id','')))
                tier = ent.get('tier','free')
                mult = 1.0
                if tier == 'supporter':
                    mult = 1.2
                elif tier == 'sponsor':
                    mult = 1.5
                elif tier == 'vip':
                    mult = 1.75
                pet['balance'] = pet.get('balance', 0) + int(round(quest.get('cash_reward', 0) * mult))
            except Exception:
                pet['balance'] = pet.get('balance', 0) + quest.get('cash_reward', 0)
            completed_quests_this_update.append(quest)

    # --- Check for Daily Completion Bonus ---
    all_daily_quests_completed_now = all(q.get('completed', False) for q in pet.get('daily_quests', []))
    if all_daily_quests_completed_now and not pet.get('claimed_daily_completion_bonus', False):
        try:
            ent = get_user_entitlements(str(pet.get('user_id','')))
            tier = ent.get('tier','free')
            mult = 1.0
            if tier == 'supporter':
                mult = 1.2
            elif tier == 'sponsor':
                mult = 1.5
            elif tier == 'vip':
                mult = 1.75
            pet['xp'] += int(round(DAILY_COMPLETION_BONUS['xp'] * mult))
        except Exception:
            pet['xp'] += DAILY_COMPLETION_BONUS['xp']
        try:
            ent = get_user_entitlements(str(pet.get('user_id','')))
            tier = ent.get('tier','free')
            mult = 1.0
            if tier == 'supporter':
                mult = 1.2
            elif tier == 'sponsor':
                mult = 1.5
            elif tier == 'vip':
                mult = 1.75
            pet['balance'] = pet.get('balance', 0) + int(round(DAILY_COMPLETION_BONUS['cash'] * mult))
        except Exception:
            pet['balance'] = pet.get('balance', 0) + DAILY_COMPLETION_BONUS['cash']
        pet['claimed_daily_completion_bonus'] = True
        daily_bonus_awarded = True


    # --- Update Achievements ---
    for achievement in pet.get('achievements', []):
        if achievement.get('completed', False):
            continue

        initial_progress = achievement.get('progress', 0)

        # Update progress based on achievement description and battle stats
        if "Win " in achievement['description']:
            achievement['progress'] = min(achievement['progress_required'], initial_progress + battle_stats.get('battles_won', 0))
        elif "battle killstreak" in achievement['description']:
             # Check current killstreak against required progress directly
            if pet.get('killstreak', 0) >= achievement['progress_required']:
                 achievement['progress'] = achievement['progress_required']
        elif "Deal" in achievement['description'] and "total damage" in achievement['description']:
            achievement['progress'] = min(achievement['progress_required'], initial_progress + battle_stats.get('damage_dealt', 0))
        elif "Land" in achievement['description'] and "critical hits" in achievement['description']:
            achievement['progress'] = min(achievement['progress_required'], initial_progress + battle_stats.get('critical_hits', 0))
        elif "Land" in achievement['description'] and "lucky hits" in achievement['description']:
            achievement['progress'] = min(achievement['progress_required'], initial_progress + battle_stats.get('lucky_hits', 0))

        # Check for completion
        if achievement['progress'] >= achievement['progress_required'] and not achievement.get('completed', False):
            achievement['completed'] = True
            try:
                ent = get_user_entitlements(str(pet.get('user_id','')))
                tier = ent.get('tier','free')
                mult = 1.0
                if tier == 'supporter':
                    mult = 1.2
                elif tier == 'sponsor':
                    mult = 1.5
                elif tier == 'vip':
                    mult = 1.75
                pet['xp'] += int(round(achievement.get('xp_reward', 0) * mult))
            except Exception:
                pet['xp'] += achievement.get('xp_reward', 0)
            try:
                ent = get_user_entitlements(str(pet.get('user_id','')))
                tier = ent.get('tier','free')
                mult = 1.0
                if tier == 'supporter':
                    mult = 1.2
                elif tier == 'sponsor':
                    mult = 1.5
                elif tier == 'vip':
                    mult = 1.75
                pet['balance'] = pet.get('balance', 0) + int(round(achievement.get('cash_reward', 0) * mult))
            except Exception:
                pet['balance'] = pet.get('balance', 0) + achievement.get('cash_reward', 0)
            completed_achievements_this_update.append(achievement)

    return completed_quests_this_update, completed_achievements_this_update, daily_bonus_awarded

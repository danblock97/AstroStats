import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config.settings import MONGODB_URI


logger = logging.getLogger(__name__)

# Users DB name: configurable via env var; default 'astrostats'. We'll also fallback to 'astrostats_database'.
USERS_DB_NAME = os.getenv("MONGODB_USERS_DB", "astrostats")
FALLBACK_USERS_DB_NAME = "astrostats_database"
USERS_COLLECTION_NAME = "users"


_mongo_client: Optional[MongoClient] = None
_users_collection = None
_fallback_users_collection = None

# Simple in-memory cache: discordId -> (expires_at_epoch_s, entitlements_dict)
_ENTITLEMENTS_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 5 * 60


def _init_db_if_needed() -> None:
    global _mongo_client, _users_collection, _fallback_users_collection
    if _mongo_client is not None and _users_collection is not None:
        return
    try:
        _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = _mongo_client[USERS_DB_NAME]
        _users_collection = db[USERS_COLLECTION_NAME]
        # prepare fallback collection handle too
        try:
            if USERS_DB_NAME != FALLBACK_USERS_DB_NAME:
                _fallback_users_collection = _mongo_client[FALLBACK_USERS_DB_NAME][USERS_COLLECTION_NAME]
            else:
                _fallback_users_collection = None
        except Exception:
            _fallback_users_collection = None
        # Light ping
        _mongo_client.admin.command("ping")
        logger.info("Premium service connected to users collection in DB '%s' (fallback: %s)", USERS_DB_NAME, FALLBACK_USERS_DB_NAME if _fallback_users_collection else None)
    except Exception as e:
        logger.error("Failed to initialize MongoDB client for premium service: %s", e, exc_info=True)
        _mongo_client = None
        _users_collection = None
        _fallback_users_collection = None


def get_user_by_discord_id(discord_id: str) -> Optional[Dict[str, Any]]:
    """Fetch the user document by exact discordId string. Returns None on not found or DB error."""
    try:
        _init_db_if_needed()
        if _users_collection is None:
            return None
        doc = _users_collection.find_one({"discordId": str(discord_id)})
        if not doc and _fallback_users_collection is not None:
            try:
                doc = _fallback_users_collection.find_one({"discordId": str(discord_id)})
            except Exception:
                pass
        return doc
    except PyMongoError as e:
        logger.error("DB error fetching user by discordId %s: %s", discord_id, e, exc_info=True)
        return None
    except Exception as e:
        logger.error("Unexpected error fetching user by discordId %s: %s", discord_id, e, exc_info=True)
        return None


def is_premium_active(user_doc: Optional[Dict[str, Any]], now_epoch_s: Optional[int] = None) -> bool:
    """Determine premium active per spec."""
    if not user_doc:
        return False
    if user_doc.get("premium") is not True:
        return False
    status = user_doc.get("status")
    if status not in {"active", "trialing"}:
        return False
    now = int(now_epoch_s if now_epoch_s is not None else time.time())
    current_period_end = user_doc.get("currentPeriodEnd")
    if current_period_end is not None:
        try:
            # Treat stored value as unix seconds
            if now >= int(current_period_end):
                return False
        except Exception:
            # If malformed, fail closed (free)
            return False
    # If cancelAtPeriodEnd true, still premium until currentPeriodEnd; already handled by date check
    return True


def _tier_entitlements(role: Optional[str]) -> Dict[str, Any]:
    # Map exactly; unknown or None -> free
    tiers: Dict[str, Dict[str, Any]] = {
        "supporter": {
            "tier": "supporter",
            "dailyPetQuestsBonus": 2,
            "extraPets": 0,
            "squibgamesMaxPlayers": 20,
            "premiumBadge": True,
            "accessToPremiumCommands": True,
        },
        "sponsor": {
            "tier": "sponsor",
            "dailyPetQuestsBonus": 5,
            "extraPets": 1,
            "squibgamesMaxPlayers": 50,
            "premiumBadge": True,
            "accessToPremiumCommands": True,
        },
        "vip": {
            "tier": "vip",
            "dailyPetQuestsBonus": 8,
            "extraPets": 3,
            "squibgamesMaxPlayers": 75,
            "premiumBadge": True,
            "accessToPremiumCommands": True,
        },
    }

    free_defaults = {
        "tier": "free",
        "dailyPetQuestsBonus": 0,
        "extraPets": 0,
        # Free tier cap for Squib Games sessions
        "squibgamesMaxPlayers": 10,
        "premiumBadge": False,
        "accessToPremiumCommands": False,
    }

    return tiers.get(role or "", free_defaults)


def get_entitlements(user_doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute entitlements for a user doc.
    - If premium active is False, return free entitlements.
    - If active, map role exactly; unknown/missing role => free entitlements.
    """
    try:
        if not is_premium_active(user_doc):
            ent = _tier_entitlements(None)
            # Reduce noise: only log free-tier decisions at DEBUG level
            logger.debug("Entitlements decision: premium=0 tier=free")
            return ent

        role = user_doc.get("role")
        ent = _tier_entitlements(role)
        logger.info(
            "Entitlements decision: premium=1 discordId=%s role=%s -> tier=%s",
            user_doc.get("discordId"), role, ent.get("tier")
        )
        return ent
    except Exception as e:
        logger.error("Error computing entitlements: %s", e, exc_info=True)
        return _tier_entitlements(None)


def get_user_entitlements(discord_id: str) -> Dict[str, Any]:
    """Get entitlements for a discordId with a 5-minute cache. On DB error, return free."""
    now = time.time()
    cache_entry = _ENTITLEMENTS_CACHE.get(str(discord_id))
    if cache_entry:
        expires_at, ent = cache_entry
        if now < expires_at:
            return ent

    try:
        user_doc = get_user_by_discord_id(str(discord_id))
        ent = get_entitlements(user_doc)
    except Exception as e:
        logger.error("Falling back to free entitlements due to error for discordId %s: %s", discord_id, e)
        ent = _tier_entitlements(None)

    _ENTITLEMENTS_CACHE[str(discord_id)] = (now + _CACHE_TTL_SECONDS, ent)
    return ent


def invalidate_user_entitlements(discord_id: str) -> None:
    """Invalidate cached entitlements for a user."""
    try:
        _ENTITLEMENTS_CACHE.pop(str(discord_id), None)
    except Exception:
        pass


__all__ = [
    "get_user_by_discord_id",
    "is_premium_active",
    "get_entitlements",
    "get_user_entitlements",
    "invalidate_user_entitlements",
]



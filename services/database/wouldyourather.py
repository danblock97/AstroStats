# services/database/wouldyourather.py
import logging
import os
from typing import Optional, Dict, Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config.settings import MONGODB_URI
from services.database.models import WouldYouRatherAutoSettings

logger = logging.getLogger(__name__)

# Database configuration
WYR_DB_NAME = os.getenv("MONGODB_WELCOME_DB", "astrostats_database")
WYR_COLLECTION_NAME = "wouldyourather_auto_settings"

_mongo_client: Optional[MongoClient] = None
_wyr_collection = None


def _init_db_if_needed() -> None:
    """Initialize database connection if needed."""
    global _mongo_client, _wyr_collection
    if _mongo_client is not None and _wyr_collection is not None:
        return
    try:
        _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=30000, connectTimeoutMS=20000, socketTimeoutMS=20000)
        db = _mongo_client[WYR_DB_NAME]
        _wyr_collection = db[WYR_COLLECTION_NAME]
        # Light ping
        _mongo_client.admin.command("ping")
        logger.debug("Would You Rather auto service connected to DB '%s'", WYR_DB_NAME)
    except Exception as e:
        logger.error("Failed to initialize MongoDB client for would you rather auto service: %s", e, exc_info=True)
        _mongo_client = None
        _wyr_collection = None


def get_wyr_auto_settings(guild_id: str) -> Optional[WouldYouRatherAutoSettings]:
    """Get would you rather auto settings for a guild."""
    try:
        _init_db_if_needed()
        if _wyr_collection is None:
            return None
        
        doc = _wyr_collection.find_one({"guild_id": str(guild_id)})
        if not doc:
            return None
            
        return WouldYouRatherAutoSettings(
            guild_id=doc["guild_id"],
            enabled=doc.get("enabled", False),
            category=doc.get("category"),
            channel_id=doc.get("channel_id"),
            _id=doc.get("_id")
        )
    except PyMongoError as e:
        logger.error("DB error fetching would you rather auto settings for guild %s: %s", guild_id, e, exc_info=True)
        return None
    except Exception as e:
        logger.error("Unexpected error fetching would you rather auto settings for guild %s: %s", guild_id, e, exc_info=True)
        return None


def update_wyr_auto_settings(guild_id: str, **kwargs) -> bool:
    """Update would you rather auto settings for a guild."""
    try:
        _init_db_if_needed()
        if _wyr_collection is None:
            return False
        
        update_doc = {"$set": {}}
        
        # Only update provided fields
        if "enabled" in kwargs:
            update_doc["$set"]["enabled"] = kwargs["enabled"]
        if "category" in kwargs:
            update_doc["$set"]["category"] = kwargs["category"]
        if "channel_id" in kwargs:
            update_doc["$set"]["channel_id"] = kwargs["channel_id"]
        
        if not update_doc["$set"]:
            return True  # No changes to make
        
        result = _wyr_collection.update_one(
            {"guild_id": str(guild_id)},
            update_doc,
            upsert=True
        )
        
        return result.acknowledged
    except PyMongoError as e:
        logger.error("DB error updating would you rather auto settings for guild %s: %s", guild_id, e, exc_info=True)
        return False
    except Exception as e:
        logger.error("Unexpected error updating would you rather auto settings for guild %s: %s", guild_id, e, exc_info=True)
        return False


def get_all_enabled_guilds() -> list:
    """Get all guilds with auto mode enabled."""
    try:
        _init_db_if_needed()
        if _wyr_collection is None:
            return []
        
        docs = _wyr_collection.find({"enabled": True})
        return list(docs)
    except PyMongoError as e:
        logger.error("DB error fetching enabled would you rather auto settings: %s", e, exc_info=True)
        return []
    except Exception as e:
        logger.error("Unexpected error fetching enabled would you rather auto settings: %s", e, exc_info=True)
        return []


__all__ = [
    "get_wyr_auto_settings",
    "update_wyr_auto_settings",
    "get_all_enabled_guilds",
    "WouldYouRatherAutoSettings",
]


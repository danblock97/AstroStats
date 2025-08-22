# services/database/welcome.py
import logging
import os
from typing import Optional, Dict, Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config.settings import MONGODB_URI
from services.database.models import WelcomeSettings

logger = logging.getLogger(__name__)

# Database configuration
WELCOME_DB_NAME = os.getenv("MONGODB_WELCOME_DB", "astrostats_database")
WELCOME_COLLECTION_NAME = "welcome_settings"

_mongo_client: Optional[MongoClient] = None
_welcome_collection = None


def _init_db_if_needed() -> None:
    """Initialize database connection if needed."""
    global _mongo_client, _welcome_collection
    if _mongo_client is not None and _welcome_collection is not None:
        return
    try:
        _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = _mongo_client[WELCOME_DB_NAME]
        _welcome_collection = db[WELCOME_COLLECTION_NAME]
        # Light ping
        _mongo_client.admin.command("ping")
        logger.info("Welcome service connected to DB '%s'", WELCOME_DB_NAME)
    except Exception as e:
        logger.error("Failed to initialize MongoDB client for welcome service: %s", e, exc_info=True)
        _mongo_client = None
        _welcome_collection = None


def get_welcome_settings(guild_id: str) -> Optional[WelcomeSettings]:
    """Get welcome settings for a guild."""
    try:
        _init_db_if_needed()
        if _welcome_collection is None:
            return None
        
        doc = _welcome_collection.find_one({"guild_id": str(guild_id)})
        if not doc:
            return None
            
        return WelcomeSettings(
            guild_id=doc["guild_id"],
            enabled=doc.get("enabled", False),
            custom_message=doc.get("custom_message"),
            custom_image_data=doc.get("custom_image_data"),
            custom_image_filename=doc.get("custom_image_filename"),
            _id=doc.get("_id")
        )
    except PyMongoError as e:
        logger.error("DB error fetching welcome settings for guild %s: %s", guild_id, e, exc_info=True)
        return None
    except Exception as e:
        logger.error("Unexpected error fetching welcome settings for guild %s: %s", guild_id, e, exc_info=True)
        return None


def update_welcome_settings(guild_id: str, **kwargs) -> bool:
    """Update welcome settings for a guild."""
    try:
        _init_db_if_needed()
        if _welcome_collection is None:
            return False
        
        update_doc = {"$set": {}}
        
        # Only update provided fields
        if "enabled" in kwargs:
            update_doc["$set"]["enabled"] = kwargs["enabled"]
        if "custom_message" in kwargs:
            update_doc["$set"]["custom_message"] = kwargs["custom_message"]
        if "custom_image_data" in kwargs:
            update_doc["$set"]["custom_image_data"] = kwargs["custom_image_data"]
        if "custom_image_filename" in kwargs:
            update_doc["$set"]["custom_image_filename"] = kwargs["custom_image_filename"]
        
        if not update_doc["$set"]:
            return True  # No changes to make
        
        result = _welcome_collection.update_one(
            {"guild_id": str(guild_id)},
            update_doc,
            upsert=True
        )
        
        return result.acknowledged
    except PyMongoError as e:
        logger.error("DB error updating welcome settings for guild %s: %s", guild_id, e, exc_info=True)
        return False
    except Exception as e:
        logger.error("Unexpected error updating welcome settings for guild %s: %s", guild_id, e, exc_info=True)
        return False


__all__ = [
    "get_welcome_settings",
    "update_welcome_settings",
    "WelcomeSettings",
]
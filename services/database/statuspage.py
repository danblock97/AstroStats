# services/database/statuspage.py
import logging
import os
from typing import Optional

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config.settings import MONGODB_URI
from services.database.models import StatusPageSettings

logger = logging.getLogger(__name__)

# Database configuration
STATUSPAGE_DB_NAME = os.getenv("MONGODB_STATUSPAGE_DB", "astrostats_database")
STATUSPAGE_COLLECTION_NAME = "statuspage_settings"

_mongo_client: Optional[MongoClient] = None
_statuspage_collection = None


def _init_db_if_needed() -> None:
    """Initialize database connection if needed."""
    global _mongo_client, _statuspage_collection
    if _mongo_client is not None and _statuspage_collection is not None:
        return
    try:
        _mongo_client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000
        )
        db = _mongo_client[STATUSPAGE_DB_NAME]
        _statuspage_collection = db[STATUSPAGE_COLLECTION_NAME]
        # Light ping
        _mongo_client.admin.command("ping")
        logger.debug("Status page service connected to DB '%s'", STATUSPAGE_DB_NAME)
    except Exception as e:
        logger.error("Failed to initialize MongoDB client for status page service: %s", e, exc_info=True)
        _mongo_client = None
        _statuspage_collection = None


def get_statuspage_settings(guild_id: str) -> Optional[StatusPageSettings]:
    """Get status page settings for a guild."""
    try:
        _init_db_if_needed()
        if _statuspage_collection is None:
            return None

        doc = _statuspage_collection.find_one({"guild_id": str(guild_id)})
        if not doc:
            return None

        return StatusPageSettings(
            guild_id=doc["guild_id"],
            enabled=doc.get("enabled", False),
            channel_id=doc.get("channel_id"),
            last_posted_update_ids=doc.get("last_posted_update_ids", []),
            _id=doc.get("_id")
        )
    except PyMongoError as e:
        logger.error("DB error fetching status page settings for guild %s: %s", guild_id, e, exc_info=True)
        return None
    except Exception as e:
        logger.error("Unexpected error fetching status page settings for guild %s: %s", guild_id, e, exc_info=True)
        return None


def update_statuspage_settings(guild_id: str, **kwargs) -> bool:
    """Update status page settings for a guild."""
    try:
        _init_db_if_needed()
        if _statuspage_collection is None:
            return False

        update_doc = {"$set": {}}

        if "enabled" in kwargs:
            update_doc["$set"]["enabled"] = kwargs["enabled"]
        if "channel_id" in kwargs:
            update_doc["$set"]["channel_id"] = kwargs["channel_id"]
        if "last_posted_update_ids" in kwargs:
            update_doc["$set"]["last_posted_update_ids"] = kwargs["last_posted_update_ids"]

        if not update_doc["$set"]:
            return True

        result = _statuspage_collection.update_one(
            {"guild_id": str(guild_id)},
            update_doc,
            upsert=True
        )
        return result.acknowledged
    except PyMongoError as e:
        logger.error("DB error updating status page settings for guild %s: %s", guild_id, e, exc_info=True)
        return False
    except Exception as e:
        logger.error("Unexpected error updating status page settings for guild %s: %s", guild_id, e, exc_info=True)
        return False


def get_all_enabled_guilds() -> list:
    """Get all guilds with status page updates enabled."""
    try:
        _init_db_if_needed()
        if _statuspage_collection is None:
            return []

        docs = _statuspage_collection.find({"enabled": True})
        return list(docs)
    except PyMongoError as e:
        logger.error("DB error fetching enabled status page settings: %s", e, exc_info=True)
        return []
    except Exception as e:
        logger.error("Unexpected error fetching enabled status page settings: %s", e, exc_info=True)
        return []


__all__ = [
    "get_statuspage_settings",
    "update_statuspage_settings",
    "get_all_enabled_guilds",
    "StatusPageSettings",
]

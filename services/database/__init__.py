import logging
import os
from types import SimpleNamespace
from typing import Optional

from pymongo import MongoClient as PyMongoClient

logger = logging.getLogger(__name__)

_mongo_client: Optional[PyMongoClient] = None


def _should_use_mock_db() -> bool:
    """Return True when tests should avoid real Mongo connections."""
    return os.getenv("ASTROSTATS_USE_MOCK_DB") == "1"


class _DummyCursor(list):
    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self


class _DummyCollection:
    def __init__(self, name: str):
        self._name = name

    def find_one(self, *args, **kwargs):
        return None

    def find(self, *args, **kwargs):
        return _DummyCursor()

    def count_documents(self, *args, **kwargs):
        return 0

    def update_one(self, *args, **kwargs):
        return SimpleNamespace(modified_count=0, matched_count=0, acknowledged=True)

    def update_many(self, *args, **kwargs):
        return SimpleNamespace(modified_count=0, matched_count=0, acknowledged=True)

    def insert_one(self, *args, **kwargs):
        return SimpleNamespace(inserted_id=None, acknowledged=True)

    def insert_many(self, *args, **kwargs):
        return SimpleNamespace(inserted_ids=[], acknowledged=True)

    def delete_one(self, *args, **kwargs):
        return SimpleNamespace(deleted_count=0, acknowledged=True)

    def aggregate(self, *args, **kwargs):
        return _DummyCursor()

    def __getattr__(self, item):
        # For any other method, return a callable that behaves like a no-op mock.
        def _noop(*_args, **_kwargs):
            return SimpleNamespace()

        _noop.__name__ = f"{self._name}.{item}"
        return _noop


class _DummyDatabase:
    def __init__(self, name: str):
        self._name = name
        self._collections = {}

    def __getitem__(self, item):
        if item not in self._collections:
            self._collections[item] = _DummyCollection(f"{self._name}.{item}")
        return self._collections[item]


class _DummyMongoClient:
    def __init__(self):
        self._databases = {}

    def __getitem__(self, item):
        if item not in self._databases:
            self._databases[item] = _DummyDatabase(item)
        return self._databases[item]

    def close(self):
        self._databases.clear()


def get_mongo_client() -> PyMongoClient:
    """
    Return a singleton Mongo client.
    Falls back to mongomock when ASTROSTATS_USE_MOCK_DB=1 to keep tests hermetic.
    """
    global _mongo_client
    if _mongo_client is not None:
        return _mongo_client

    if _should_use_mock_db():
        try:
            from mongomock import MongoClient as MockMongoClient
            _mongo_client = MockMongoClient()
            logger.debug("Initialized mongomock MongoClient for testing.")
            return _mongo_client
        except ImportError:
            logger.debug("mongomock not available; using dummy Mongo client for tests.")
            _mongo_client = _DummyMongoClient()
            return _mongo_client

    from config.settings import MONGODB_URI

    _mongo_client = PyMongoClient(MONGODB_URI)
    logger.debug("Initialized real MongoClient for URI %s", MONGODB_URI)
    return _mongo_client

"""MongoDB Connection Manager for FarmShield.
Provides singleton database client, connection lifecycle, and health checking.
"""

import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoDBManager:
    client: Optional[MongoClient] = None
    db: Optional[Database] = None

    _checked: bool = False

    @classmethod
    def connect(cls) -> Optional[Database]:
        if not cls._checked:
            cls._checked = True
            try:
                logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
                client = MongoClient(
                    settings.MONGODB_URI,
                    serverSelectionTimeoutMS=1000,
                    connectTimeoutMS=1000,
                )
                # Ping database to verify connection
                client.admin.command("ping")
                cls.client = client
                cls.db = cls.client[settings.MONGODB_DATABASE]
                logger.info(f"Successfully connected to MongoDB database '{settings.MONGODB_DATABASE}'.")
            except Exception as e:
                logger.warning(f"Could not connect to live MongoDB: {e}. Operating in in-memory fallback mode.")
                cls.client = None
                cls.db = None
        return cls.db

    @classmethod
    def get_database(cls) -> Optional[Database]:
        if not cls._checked:
            return cls.connect()
        return cls.db

    @classmethod
    def close(cls):
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("MongoDB connection closed.")

    @classmethod
    def is_healthy(cls) -> bool:
        if cls.client is None:
            return False
        try:
            cls.client.admin.command("ping")
            return True
        except Exception:
            return False


def get_db() -> Database:
    """Dependency helper to get active database instance."""
    return MongoDBManager.get_database()

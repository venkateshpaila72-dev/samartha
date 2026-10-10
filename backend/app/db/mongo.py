"""MongoDB Connection Manager for FarmShield.
Provides singleton database client, connection lifecycle, DNS resilience, and health checking.
"""

import logging
import re
import time
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure DNS resolver to avoid timeouts on local unroutable network interfaces
try:
    import dns.resolver
    _resolver = dns.resolver.get_default_resolver()
    _public_dns = ["8.8.8.8", "1.1.1.1"]
    _resolver.nameservers = _public_dns + [ns for ns in _resolver.nameservers if ns not in _public_dns]
    _resolver.lifetime = 10.0
except Exception:
    pass


class MongoDBManager:
    client: Optional[MongoClient] = None
    db: Optional[Database] = None

    @classmethod
    def connect(cls) -> Optional[Database]:
        """Establish connection to MongoDB with retry capabilities and 10s timeout."""
        if settings.APP_ENV == "test":
            logger.info("Running in test environment (APP_ENV=test). In-memory test repository mode enabled.")
            cls.client = None
            cls.db = None
            return None

        if cls.client is not None and cls.db is not None:
            return cls.db

        safe_uri = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', settings.MONGODB_URI)
        logger.info(f"Connecting to MongoDB at {safe_uri}...")

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                client = MongoClient(
                    settings.MONGODB_URI,
                    serverSelectionTimeoutMS=10000,
                    connectTimeoutMS=10000,
                )
                # Ping database to verify connection
                client.admin.command("ping")
                cls.client = client
                cls.db = cls.client[settings.MONGODB_DATABASE]
                logger.info(f"Successfully connected to MongoDB database '{settings.MONGODB_DATABASE}'.")
                return cls.db
            except Exception as e:
                logger.warning(f"MongoDB connection attempt {attempt}/{max_attempts} failed: {e}")
                if attempt < max_attempts:
                    time.sleep(1)

        logger.error(f"Failed to connect to MongoDB ({safe_uri}) after {max_attempts} attempts.")
        cls.client = None
        cls.db = None
        return None

    @classmethod
    def get_database(cls) -> Optional[Database]:
        if cls.db is None and settings.APP_ENV != "test":
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


def get_db() -> Optional[Database]:
    """Dependency helper to get active database instance."""
    return MongoDBManager.get_database()

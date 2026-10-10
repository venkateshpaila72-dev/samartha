"""MongoDB Index Management for FarmShield.
Creates required unique and compound indexes for performant querying and data integrity.
"""

import logging
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.db.collection_names import (
    USERS_COLLECTION,
    CROP_PROFILES_COLLECTION,
    STORAGE_BATCHES_COLLECTION,
    SENSOR_READINGS_COLLECTION,
    FARMER_DIARY_COLLECTION,
    STORAGE_ALERTS_COLLECTION,
    CONVERSATIONS_COLLECTION,
    MESSAGES_COLLECTION,
    MARKET_PRICES_COLLECTION,
    WEATHER_RECORDS_COLLECTION,
    NOTIFICATION_LOGS_COLLECTION,
    AUDIT_LOGS_COLLECTION,
)

logger = logging.getLogger(__name__)


def create_all_indexes(db: Database) -> dict[str, list[str]]:
    """Create all required indexes across collections."""
    results = {}

    if db is None:
        logger.warning("Database instance is None, skipping index creation.")
        return results

    try:
        # Users indexes
        db[USERS_COLLECTION].create_index([("email", ASCENDING)], unique=True)
        db[USERS_COLLECTION].create_index([("role", ASCENDING)])
        results[USERS_COLLECTION] = ["email (unique)", "role"]

        # Crop Profiles indexes
        db[CROP_PROFILES_COLLECTION].create_index([("crop_id", ASCENDING)], unique=True)
        db[CROP_PROFILES_COLLECTION].create_index([("crop_name", ASCENDING)])
        db[CROP_PROFILES_COLLECTION].create_index([("crop_category", ASCENDING)])
        db[CROP_PROFILES_COLLECTION].create_index([("is_active", ASCENDING)])
        results[CROP_PROFILES_COLLECTION] = ["crop_id (unique)", "crop_name", "category", "is_active"]

        # Storage Batches indexes
        db[STORAGE_BATCHES_COLLECTION].create_index([("farmer_id", ASCENDING), ("status", ASCENDING)])
        db[STORAGE_BATCHES_COLLECTION].create_index([("crop_id", ASCENDING)])
        db[STORAGE_BATCHES_COLLECTION].create_index([("batch_id", ASCENDING)], unique=True)
        results[STORAGE_BATCHES_COLLECTION] = ["farmer_id + status", "crop_id", "batch_id (unique)"]

        # Sensor Readings indexes
        db[SENSOR_READINGS_COLLECTION].create_index(
            [("batch_id", ASCENDING), ("timestamp", DESCENDING)]
        )
        db[SENSOR_READINGS_COLLECTION].create_index([("sensor_id", ASCENDING)])
        results[SENSOR_READINGS_COLLECTION] = ["batch_id + timestamp", "sensor_id"]

        # Farmer Diary Entries indexes
        db[FARMER_DIARY_COLLECTION].create_index(
            [("batch_id", ASCENDING), ("created_at", DESCENDING)]
        )
        db[FARMER_DIARY_COLLECTION].create_index([("farmer_id", ASCENDING)])
        results[FARMER_DIARY_COLLECTION] = ["batch_id + created_at", "farmer_id"]

        # Storage Alerts indexes
        db[STORAGE_ALERTS_COLLECTION].create_index(
            [("batch_id", ASCENDING), ("status", ASCENDING)]
        )
        db[STORAGE_ALERTS_COLLECTION].create_index([("created_at", DESCENDING)])
        db[STORAGE_ALERTS_COLLECTION].create_index([("severity", ASCENDING)])
        results[STORAGE_ALERTS_COLLECTION] = ["batch_id + status", "created_at", "severity"]

        # Conversations & Messages indexes
        db[CONVERSATIONS_COLLECTION].create_index([("user_id", ASCENDING)])
        db[CONVERSATIONS_COLLECTION].create_index([("batch_id", ASCENDING)])
        db[MESSAGES_COLLECTION].create_index(
            [("conversation_id", ASCENDING), ("timestamp", ASCENDING)]
        )
        results[CONVERSATIONS_COLLECTION] = ["user_id", "batch_id"]
        results[MESSAGES_COLLECTION] = ["conversation_id + timestamp"]

        # Market Prices & Weather
        db[MARKET_PRICES_COLLECTION].create_index([("crop", ASCENDING), ("market", ASCENDING), ("date", DESCENDING)])
        db[MARKET_PRICES_COLLECTION].create_index([("source_record_id", ASCENDING)], unique=True, sparse=True)
        db[WEATHER_RECORDS_COLLECTION].create_index([("location", ASCENDING), ("timestamp", DESCENDING)])
        results[MARKET_PRICES_COLLECTION] = ["crop + market + date"]
        results[WEATHER_RECORDS_COLLECTION] = ["location + timestamp"]

        # Notification & Audit Logs
        db[NOTIFICATION_LOGS_COLLECTION].create_index([("batch_id", ASCENDING)])
        db[NOTIFICATION_LOGS_COLLECTION].create_index([("created_at", DESCENDING)])
        db[AUDIT_LOGS_COLLECTION].create_index([("timestamp", DESCENDING)])
        results[NOTIFICATION_LOGS_COLLECTION] = ["batch_id", "created_at"]
        results[AUDIT_LOGS_COLLECTION] = ["timestamp"]

        logger.info("Successfully created all MongoDB indexes for FarmShield.")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        raise e

    return results

"""Crop Storage Profiles Database Seeding Script for FarmShield.

Reads verified Indian agricultural data, validates constraints, connects to MongoDB,
creates indexes, and idempotently upserts crop profiles.

Usage:
    cd backend
    python -m scripts.seed_crop_storage_profiles
    # Or with --overwrite to replace existing customized records:
    python -m scripts.seed_crop_storage_profiles --overwrite
"""

import argparse
import datetime
import json
import logging
import sys
from pathlib import Path

# Add backend directory to path if run directly
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.db.collection_names import CROP_PROFILES_COLLECTION, KNOWLEDGE_SOURCES_COLLECTION
from app.db.indexes import create_all_indexes
from app.db.mongo import MongoDBManager
from scripts.validate_crop_data import validate_profile

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def seed_database(overwrite: bool = False) -> bool:
    data_file = BACKEND_DIR / "data" / "crop_storage_profiles.json"
    trad_file = BACKEND_DIR / "data" / "traditional_knowledge_rag.json"

    if not data_file.exists():
        logger.error(f"Crop dataset file not found at {data_file}")
        return False

    with open(data_file, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    logger.info(f"Loaded {len(profiles)} crop profiles for validation...")
    validation_failures = 0
    for idx, p in enumerate(profiles):
        errors = validate_profile(p, idx)
        if errors:
            validation_failures += 1
            for err in errors:
                logger.error(err)

    if validation_failures > 0:
        logger.error(f"Aborting seed: {validation_failures} crop profiles failed validation.")
        return False

    logger.info("Connecting to MongoDB...")
    try:
        db = MongoDBManager.connect()
        if db is None or not MongoDBManager.is_healthy():
            logger.error(f"Cannot connect to MongoDB at '{settings.MONGODB_URI}'. Please ensure MongoDB is running.")
            return False
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False

    logger.info("Ensuring database indexes...")
    try:
        create_all_indexes(db)
    except Exception as e:
        logger.warning(f"Notice while creating indexes: {e}")

    crop_col = db[CROP_PROFILES_COLLECTION]

    inserted_count = 0
    updated_count = 0
    skipped_count = 0

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for p in profiles:
        crop_id = p["crop_id"]
        existing = crop_col.find_one({"crop_id": crop_id})

        if existing:
            # Check if record has been customized by an admin
            if existing.get("is_admin_customized", False) and not overwrite:
                logger.info(f"Skipping admin-customized record: '{crop_id}'")
                skipped_count += 1
                continue

            doc = p.copy()
            doc["updated_at"] = now_iso
            crop_col.update_one({"crop_id": crop_id}, {"$set": doc})
            updated_count += 1
        else:
            doc = p.copy()
            doc["created_at"] = now_iso
            doc["updated_at"] = now_iso
            doc["is_admin_customized"] = False
            crop_col.insert_one(doc)
            inserted_count += 1

    # Also seed traditional knowledge RAG documents if available
    trad_seeded = 0
    if trad_file.exists():
        with open(trad_file, "r", encoding="utf-8") as tf:
            trad_docs = json.load(tf)
        know_col = db[KNOWLEDGE_SOURCES_COLLECTION]
        for td in trad_docs:
            know_col.update_one(
                {"id": td["id"]},
                {"$set": td},
                upsert=True,
            )
            trad_seeded += 1

    logger.info("=" * 60)
    logger.info("SEEDING COMPLETE SUMMARY:")
    logger.info(f"  Total Validated Profiles : {len(profiles)}")
    logger.info(f"  Inserted New Records     : {inserted_count}")
    logger.info(f"  Updated Existing Records : {updated_count}")
    logger.info(f"  Skipped Records          : {skipped_count}")
    logger.info(f"  Traditional RAG Documents: {trad_seeded}")
    logger.info("=" * 60)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed FarmShield Crop Storage Profiles into MongoDB")
    parser.add_argument("--overwrite", action="store_true", help="Force overwrite admin-customized profiles")
    args = parser.parse_args()

    success = seed_database(overwrite=args.overwrite)
    sys.exit(0 if success else 1)

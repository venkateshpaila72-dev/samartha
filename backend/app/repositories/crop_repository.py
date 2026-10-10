"""Crop Profile Repository for MongoDB.
Interacts with crop_storage_profiles collection and provides fallback loading
from validated seed data to guarantee the crop database is never empty.
"""

import json
from pathlib import Path
from typing import Optional
from app.db.collection_names import CROP_PROFILES_COLLECTION
from app.db.mongo import get_db

_FALLBACK_CROP_CACHE: dict[str, dict] = {}


def _load_fallback_seed_data():
    global _FALLBACK_CROP_CACHE
    if not _FALLBACK_CROP_CACHE:
        data_path = Path(__file__).resolve().parent.parent.parent / "data" / "crop_storage_profiles.json"
        if data_path.exists():
            with open(data_path, "r", encoding="utf-8") as f:
                items = json.load(f)
                for item in items:
                    _FALLBACK_CROP_CACHE[item["crop_id"]] = item


class CropRepository:
    @staticmethod
    def _collection():
        db = get_db()
        return db[CROP_PROFILES_COLLECTION] if db is not None else None

    @classmethod
    def get_by_id(cls, crop_id: str) -> Optional[dict]:
        col = cls._collection()
        if col is not None:
            doc = col.find_one({"crop_id": crop_id, "is_active": True})
            if doc:
                doc.pop("_id", None)
                return doc
        _load_fallback_seed_data()
        return _FALLBACK_CROP_CACHE.get(crop_id)

    @classmethod
    def list_all(cls, category: Optional[str] = None, search: Optional[str] = None) -> list[dict]:
        col = cls._collection()
        query = {"is_active": True}
        if category:
            query["crop_category"] = category
        if search:
            query["crop_name"] = {"$regex": search, "$options": "i"}

        if col is not None:
            docs = list(col.find(query))
            if docs:
                for d in docs:
                    d.pop("_id", None)
                return docs

        _load_fallback_seed_data()
        results = list(_FALLBACK_CROP_CACHE.values())
        if category:
            results = [r for r in results if r.get("crop_category") == category]
        if search:
            search_lower = search.lower()
            results = [r for r in results if search_lower in r.get("crop_name", "").lower()]
        return results

    @classmethod
    def create_or_update(cls, profile: dict) -> dict:
        crop_id = profile["crop_id"]
        col = cls._collection()
        if col is not None:
            col.replace_one({"crop_id": crop_id}, profile, upsert=True)
        _FALLBACK_CROP_CACHE[crop_id] = profile.copy()
        return profile

    @classmethod
    def count(cls) -> int:
        col = cls._collection()
        if col is not None:
            c = col.count_documents({})
            if c > 0:
                return c
        _load_fallback_seed_data()
        return len(_FALLBACK_CROP_CACHE)

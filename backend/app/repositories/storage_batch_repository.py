"""Storage Batch Repository for MongoDB with isolated test storage."""

from typing import Optional
from fastapi import HTTPException, status
from app.core.config import settings
from app.db.collection_names import STORAGE_BATCHES_COLLECTION
from app.db.mongo import get_db

_IN_MEMORY_BATCHES: dict[str, dict] = {}


class StorageBatchRepository:
    @staticmethod
    def _is_test() -> bool:
        return settings.APP_ENV == "test"

    @classmethod
    def _collection(cls):
        if cls._is_test():
            return None
        db = get_db()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable.",
            )
        return db[STORAGE_BATCHES_COLLECTION]

    @classmethod
    def get_by_id(cls, batch_id: str) -> Optional[dict]:
        if cls._is_test():
            return _IN_MEMORY_BATCHES.get(batch_id)
        col = cls._collection()
        doc = col.find_one({"batch_id": batch_id})
        if doc:
            doc.pop("_id", None)
        return doc

    @classmethod
    def list_by_farmer(cls, farmer_id: str, status: Optional[str] = None) -> list[dict]:
        if cls._is_test():
            items = [
                b for b in _IN_MEMORY_BATCHES.values()
                if b.get("farmer_id") == farmer_id or b.get("user_id") == farmer_id
            ]
            if status:
                items = [b for b in items if b.get("status") == status]
            return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)

        col = cls._collection()
        query: dict = {"$or": [{"farmer_id": farmer_id}, {"user_id": farmer_id}]}
        if status:
            query = {"$and": [{"$or": [{"farmer_id": farmer_id}, {"user_id": farmer_id}]}, {"status": status}]}
        docs = list(col.find(query).sort("created_at", -1))
        for d in docs:
            d.pop("_id", None)
        return docs

    @classmethod
    def create(cls, batch_data: dict) -> dict:
        data = batch_data.copy()
        if "user_id" not in data and "farmer_id" in data:
            data["user_id"] = data["farmer_id"]
        if "farmer_id" not in data and "user_id" in data:
            data["farmer_id"] = data["user_id"]

        if cls._is_test():
            _IN_MEMORY_BATCHES[data["batch_id"]] = data.copy()
            return data

        col = cls._collection()
        doc = data.copy()
        col.replace_one({"batch_id": doc["batch_id"]}, doc, upsert=True)
        return data

    @classmethod
    def update(cls, batch_id: str, updates: dict) -> Optional[dict]:
        if cls._is_test():
            if batch_id in _IN_MEMORY_BATCHES:
                _IN_MEMORY_BATCHES[batch_id].update(updates)
            return _IN_MEMORY_BATCHES.get(batch_id)

        col = cls._collection()
        col.update_one({"batch_id": batch_id}, {"$set": updates})
        return cls.get_by_id(batch_id)

    @classmethod
    def list_all(cls, skip: int = 0, limit: int = 50) -> list[dict]:
        if cls._is_test():
            return list(_IN_MEMORY_BATCHES.values())[skip : skip + limit]

        col = cls._collection()
        docs = list(col.find().skip(skip).limit(limit))
        for d in docs:
            d.pop("_id", None)
        return docs

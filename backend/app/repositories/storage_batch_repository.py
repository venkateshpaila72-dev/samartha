"""Storage Batch Repository for MongoDB."""

from typing import Optional
from app.db.collection_names import STORAGE_BATCHES_COLLECTION
from app.db.mongo import get_db

_IN_MEMORY_BATCHES: dict[str, dict] = {}


class StorageBatchRepository:
    @staticmethod
    def _collection():
        db = get_db()
        return db[STORAGE_BATCHES_COLLECTION] if db is not None else None

    @classmethod
    def get_by_id(cls, batch_id: str) -> Optional[dict]:
        col = cls._collection()
        if col is not None:
            doc = col.find_one({"batch_id": batch_id})
            if doc:
                doc.pop("_id", None)
                return doc
        return _IN_MEMORY_BATCHES.get(batch_id)

    @classmethod
    def list_by_farmer(cls, farmer_id: str, status: Optional[str] = None) -> list[dict]:
        col = cls._collection()
        query = {"farmer_id": farmer_id}
        if status:
            query["status"] = status
        if col is not None:
            docs = list(col.find(query).sort("created_at", -1))
            if docs:
                for d in docs:
                    d.pop("_id", None)
                return docs
        items = [b for b in _IN_MEMORY_BATCHES.values() if b["farmer_id"] == farmer_id]
        if status:
            items = [b for b in items if b.get("status") == status]
        return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)

    @classmethod
    def create(cls, batch_data: dict) -> dict:
        _IN_MEMORY_BATCHES[batch_data["batch_id"]] = batch_data.copy()
        col = cls._collection()
        if col is not None:
            doc = batch_data.copy()
            col.replace_one({"batch_id": doc["batch_id"]}, doc, upsert=True)
        return batch_data

    @classmethod
    def update(cls, batch_id: str, updates: dict) -> Optional[dict]:
        if batch_id in _IN_MEMORY_BATCHES:
            _IN_MEMORY_BATCHES[batch_id].update(updates)
        col = cls._collection()
        if col is not None:
            col.update_one({"batch_id": batch_id}, {"$set": updates})
            return cls.get_by_id(batch_id)
        return _IN_MEMORY_BATCHES.get(batch_id)

    @classmethod
    def list_all(cls, skip: int = 0, limit: int = 50) -> list[dict]:
        col = cls._collection()
        if col is not None:
            docs = list(col.find().skip(skip).limit(limit))
            for d in docs:
                d.pop("_id", None)
            if docs:
                return docs
        return list(_IN_MEMORY_BATCHES.values())[skip : skip + limit]

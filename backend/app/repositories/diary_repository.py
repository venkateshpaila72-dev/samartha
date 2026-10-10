"""Farmer Diary Repository for MongoDB."""

from typing import Optional
from app.db.collection_names import FARMER_DIARY_COLLECTION
from app.db.mongo import get_db

_IN_MEMORY_DIARY: dict[str, dict] = {}


class DiaryRepository:
    @staticmethod
    def _collection():
        db = get_db()
        return db[FARMER_DIARY_COLLECTION] if db is not None else None

    @classmethod
    def get_by_id(cls, entry_id: str) -> Optional[dict]:
        col = cls._collection()
        if col is not None:
            doc = col.find_one({"entry_id": entry_id})
            if doc:
                doc.pop("_id", None)
                return doc
        return _IN_MEMORY_DIARY.get(entry_id)

    @classmethod
    def list_by_batch(cls, batch_id: str) -> list[dict]:
        col = cls._collection()
        if col is not None:
            docs = list(col.find({"batch_id": batch_id}).sort("created_at", -1))
            if docs:
                for d in docs:
                    d.pop("_id", None)
                return docs
        entries = [e for e in _IN_MEMORY_DIARY.values() if e["batch_id"] == batch_id]
        return sorted(entries, key=lambda x: x["created_at"], reverse=True)

    @classmethod
    def create(cls, entry_data: dict) -> dict:
        _IN_MEMORY_DIARY[entry_data["entry_id"]] = entry_data.copy()
        col = cls._collection()
        if col is not None:
            col.insert_one(entry_data.copy())
        return entry_data

    @classmethod
    def update(cls, entry_id: str, updates: dict) -> Optional[dict]:
        if entry_id in _IN_MEMORY_DIARY:
            _IN_MEMORY_DIARY[entry_id].update(updates)
        col = cls._collection()
        if col is not None:
            col.update_one({"entry_id": entry_id}, {"$set": updates})
            return cls.get_by_id(entry_id)
        return _IN_MEMORY_DIARY.get(entry_id)

    @classmethod
    def delete(cls, entry_id: str) -> bool:
        deleted = False
        if entry_id in _IN_MEMORY_DIARY:
            del _IN_MEMORY_DIARY[entry_id]
            deleted = True
        col = cls._collection()
        if col is not None:
            res = col.delete_one({"entry_id": entry_id})
            if res.deleted_count > 0:
                deleted = True
        return deleted

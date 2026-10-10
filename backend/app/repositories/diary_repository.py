"""Farmer Diary Repository for MongoDB with isolated test storage."""

from typing import Optional
from fastapi import HTTPException, status
from app.core.config import settings
from app.db.collection_names import FARMER_DIARY_COLLECTION
from app.db.mongo import get_db

_IN_MEMORY_DIARY: dict[str, dict] = {}


class DiaryRepository:
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
        return db[FARMER_DIARY_COLLECTION]

    @classmethod
    def get_by_id(cls, entry_id: str) -> Optional[dict]:
        if cls._is_test():
            return _IN_MEMORY_DIARY.get(entry_id)
        col = cls._collection()
        doc = col.find_one({"entry_id": entry_id})
        if doc:
            doc.pop("_id", None)
        return doc

    @classmethod
    def list_by_batch(cls, batch_id: str) -> list[dict]:
        if cls._is_test():
            entries = [e for e in _IN_MEMORY_DIARY.values() if e["batch_id"] == batch_id]
            return sorted(entries, key=lambda x: x["created_at"], reverse=True)

        col = cls._collection()
        docs = list(col.find({"batch_id": batch_id}).sort("created_at", -1))
        for d in docs:
            d.pop("_id", None)
        return docs

    @classmethod
    def create(cls, entry_data: dict) -> dict:
        if cls._is_test():
            _IN_MEMORY_DIARY[entry_data["entry_id"]] = entry_data.copy()
            return entry_data

        col = cls._collection()
        col.insert_one(entry_data.copy())
        return entry_data

    @classmethod
    def update(cls, entry_id: str, updates: dict) -> Optional[dict]:
        if cls._is_test():
            if entry_id in _IN_MEMORY_DIARY:
                _IN_MEMORY_DIARY[entry_id].update(updates)
            return _IN_MEMORY_DIARY.get(entry_id)

        col = cls._collection()
        col.update_one({"entry_id": entry_id}, {"$set": updates})
        return cls.get_by_id(entry_id)

    @classmethod
    def delete(cls, entry_id: str) -> bool:
        if cls._is_test():
            if entry_id in _IN_MEMORY_DIARY:
                del _IN_MEMORY_DIARY[entry_id]
                return True
            return False

        col = cls._collection()
        res = col.delete_one({"entry_id": entry_id})
        return res.deleted_count > 0

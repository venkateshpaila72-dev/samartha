"""User Repository for MongoDB with isolated test storage."""

from typing import Optional
from fastapi import HTTPException, status
from app.core.config import settings
from app.db.collection_names import USERS_COLLECTION
from app.db.mongo import get_db

_IN_MEMORY_USERS: dict[str, dict] = {}


class UserRepository:
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
        return db[USERS_COLLECTION]

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional[dict]:
        if cls._is_test():
            return _IN_MEMORY_USERS.get(user_id)
        col = cls._collection()
        doc = col.find_one({"id": user_id})
        if doc:
            doc.pop("_id", None)
        return doc

    @classmethod
    def get_by_email(cls, email: str) -> Optional[dict]:
        email_clean = email.strip().lower()
        if cls._is_test():
            for u in _IN_MEMORY_USERS.values():
                if u["email"].lower() == email_clean:
                    return u
            return None
        col = cls._collection()
        doc = col.find_one({"email": email_clean})
        if doc:
            doc.pop("_id", None)
        return doc

    @classmethod
    def create(cls, user_data: dict) -> dict:
        user_data["email"] = user_data["email"].strip().lower()
        if cls._is_test():
            _IN_MEMORY_USERS[user_data["id"]] = user_data.copy()
            return user_data
        col = cls._collection()
        doc = user_data.copy()
        col.replace_one({"id": doc["id"]}, doc, upsert=True)
        return user_data

    @classmethod
    def update(cls, user_id: str, updates: dict) -> Optional[dict]:
        if cls._is_test():
            if user_id in _IN_MEMORY_USERS:
                _IN_MEMORY_USERS[user_id].update(updates)
            return _IN_MEMORY_USERS.get(user_id)
        col = cls._collection()
        col.update_one({"id": user_id}, {"$set": updates})
        return cls.get_by_id(user_id)

    @classmethod
    def list_all(cls, skip: int = 0, limit: int = 50) -> list[dict]:
        if cls._is_test():
            return list(_IN_MEMORY_USERS.values())[skip : skip + limit]
        col = cls._collection()
        docs = list(col.find().skip(skip).limit(limit))
        for d in docs:
            d.pop("_id", None)
        return docs

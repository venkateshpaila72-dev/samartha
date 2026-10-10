"""User Repository for MongoDB with in-memory test fallback."""

from typing import Optional
from app.db.collection_names import USERS_COLLECTION
from app.db.mongo import get_db

# In-memory storage for test isolation / fallback
_IN_MEMORY_USERS = {}


class UserRepository:
    @staticmethod
    def _collection():
        db = get_db()
        return db[USERS_COLLECTION] if db is not None else None

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional[dict]:
        col = cls._collection()
        if col is not None:
            doc = col.find_one({"id": user_id})
            if doc:
                doc.pop("_id", None)
                return doc
        return _IN_MEMORY_USERS.get(user_id)

    @classmethod
    def get_by_email(cls, email: str) -> Optional[dict]:
        email_clean = email.strip().lower()
        col = cls._collection()
        if col is not None:
            doc = col.find_one({"email": email_clean})
            if doc:
                doc.pop("_id", None)
                return doc
        for u in _IN_MEMORY_USERS.values():
            if u["email"].lower() == email_clean:
                return u
        return None

    @classmethod
    def create(cls, user_data: dict) -> dict:
        user_data["email"] = user_data["email"].strip().lower()
        _IN_MEMORY_USERS[user_data["id"]] = user_data.copy()
        col = cls._collection()
        if col is not None:
            doc = user_data.copy()
            col.replace_one({"id": doc["id"]}, doc, upsert=True)
        return user_data

    @classmethod
    def update(cls, user_id: str, updates: dict) -> Optional[dict]:
        if user_id in _IN_MEMORY_USERS:
            _IN_MEMORY_USERS[user_id].update(updates)
        col = cls._collection()
        if col is not None:
            col.update_one({"id": user_id}, {"$set": updates})
            return cls.get_by_id(user_id)
        return _IN_MEMORY_USERS.get(user_id)

    @classmethod
    def list_all(cls, skip: int = 0, limit: int = 50) -> list[dict]:
        col = cls._collection()
        if col is not None:
            docs = list(col.find().skip(skip).limit(limit))
            for d in docs:
                d.pop("_id", None)
            if docs:
                return docs
        return list(_IN_MEMORY_USERS.values())[skip : skip + limit]

"""Storage Alert Repository for MongoDB with isolated test storage."""

from typing import Optional
from fastapi import HTTPException, status
from app.core.config import settings
from app.db.collection_names import STORAGE_ALERTS_COLLECTION
from app.db.mongo import get_db

_IN_MEMORY_ALERTS: dict[str, dict] = {}


class AlertRepository:
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
        return db[STORAGE_ALERTS_COLLECTION]

    @classmethod
    def get_by_id(cls, alert_id: str) -> Optional[dict]:
        if cls._is_test():
            return _IN_MEMORY_ALERTS.get(alert_id)
        col = cls._collection()
        doc = col.find_one({"alert_id": alert_id})
        if doc:
            doc.pop("_id", None)
        return doc

    @classmethod
    def list_by_batch(cls, batch_id: str, status: Optional[str] = None) -> list[dict]:
        if cls._is_test():
            alerts = [a for a in _IN_MEMORY_ALERTS.values() if a["batch_id"] == batch_id]
            if status:
                alerts = [a for a in alerts if a["status"] == status]
            return sorted(alerts, key=lambda x: x["created_at"], reverse=True)

        col = cls._collection()
        query = {"batch_id": batch_id}
        if status:
            query["status"] = status
        docs = list(col.find(query).sort("created_at", -1))
        for d in docs:
            d.pop("_id", None)
        return docs

    @classmethod
    def list_all(cls, status: Optional[str] = None) -> list[dict]:
        if cls._is_test():
            alerts = list(_IN_MEMORY_ALERTS.values())
            if status:
                alerts = [a for a in alerts if a["status"] == status]
            return sorted(alerts, key=lambda x: x["created_at"], reverse=True)

        col = cls._collection()
        query = {}
        if status:
            query["status"] = status
        docs = list(col.find(query).sort("created_at", -1))
        for d in docs:
            d.pop("_id", None)
        return docs

    @classmethod
    def get_active_condition(cls, batch_id: str, condition_type: str) -> Optional[dict]:
        if cls._is_test():
            for a in _IN_MEMORY_ALERTS.values():
                if a["batch_id"] == batch_id and a["condition_type"] == condition_type and a["status"] in ["active", "acknowledged"]:
                    return a
            return None

        col = cls._collection()
        query = {
            "batch_id": batch_id,
            "condition_type": condition_type,
            "status": {"$in": ["active", "acknowledged"]},
        }
        doc = col.find_one(query)
        if doc:
            doc.pop("_id", None)
        return doc

    @classmethod
    def create(cls, alert_data: dict) -> dict:
        if cls._is_test():
            _IN_MEMORY_ALERTS[alert_data["alert_id"]] = alert_data.copy()
            return alert_data

        col = cls._collection()
        col.insert_one(alert_data.copy())
        return alert_data

    @classmethod
    def update(cls, alert_id: str, updates: dict) -> Optional[dict]:
        if cls._is_test():
            if alert_id in _IN_MEMORY_ALERTS:
                _IN_MEMORY_ALERTS[alert_id].update(updates)
            return _IN_MEMORY_ALERTS.get(alert_id)

        col = cls._collection()
        col.update_one({"alert_id": alert_id}, {"$set": updates})
        return cls.get_by_id(alert_id)

    @classmethod
    def update_status(cls, alert_id: str, status: str, resolved_at: Optional[str] = None) -> Optional[dict]:
        updates = {"status": status}
        if resolved_at:
            updates["resolved_at"] = resolved_at
        return cls.update(alert_id, updates)

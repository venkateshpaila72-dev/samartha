"""Storage Alert Repository for MongoDB."""

from typing import Optional
from app.db.collection_names import STORAGE_ALERTS_COLLECTION
from app.db.mongo import get_db

_IN_MEMORY_ALERTS: dict[str, dict] = {}


class AlertRepository:
    @staticmethod
    def _collection():
        db = get_db()
        return db[STORAGE_ALERTS_COLLECTION] if db is not None else None

    @classmethod
    def get_by_id(cls, alert_id: str) -> Optional[dict]:
        col = cls._collection()
        if col is not None:
            doc = col.find_one({"alert_id": alert_id})
            if doc:
                doc.pop("_id", None)
                return doc
        return _IN_MEMORY_ALERTS.get(alert_id)

    @classmethod
    def list_by_batch(cls, batch_id: str, status: Optional[str] = None) -> list[dict]:
        col = cls._collection()
        query = {"batch_id": batch_id}
        if status:
            query["status"] = status
        if col is not None:
            docs = list(col.find(query).sort("created_at", -1))
            if docs:
                for d in docs:
                    d.pop("_id", None)
                return docs
        alerts = [a for a in _IN_MEMORY_ALERTS.values() if a["batch_id"] == batch_id]
        if status:
            alerts = [a for a in alerts if a["status"] == status]
        return sorted(alerts, key=lambda x: x["created_at"], reverse=True)

    @classmethod
    def list_all(cls, status: Optional[str] = None) -> list[dict]:
        col = cls._collection()
        query = {}
        if status:
            query["status"] = status
        if col is not None:
            docs = list(col.find(query).sort("created_at", -1))
            if docs:
                for d in docs:
                    d.pop("_id", None)
                return docs
        alerts = list(_IN_MEMORY_ALERTS.values())
        if status:
            alerts = [a for a in alerts if a["status"] == status]
        return sorted(alerts, key=lambda x: x["created_at"], reverse=True)

    @classmethod
    def get_active_condition(cls, batch_id: str, condition_type: str) -> Optional[dict]:
        col = cls._collection()
        query = {"batch_id": batch_id, "condition_type": condition_type, "status": "active"}
        if col is not None:
            doc = col.find_one(query)
            if doc:
                doc.pop("_id", None)
                return doc
        for a in _IN_MEMORY_ALERTS.values():
            if a["batch_id"] == batch_id and a["condition_type"] == condition_type and a["status"] == "active":
                return a
        return None

    @classmethod
    def create(cls, alert_data: dict) -> dict:
        _IN_MEMORY_ALERTS[alert_data["alert_id"]] = alert_data.copy()
        col = cls._collection()
        if col is not None:
            col.insert_one(alert_data.copy())
        return alert_data

    @classmethod
    def update_status(cls, alert_id: str, status: str, resolved_at: Optional[str] = None) -> Optional[dict]:
        updates = {"status": status}
        if resolved_at:
            updates["resolved_at"] = resolved_at
        if alert_id in _IN_MEMORY_ALERTS:
            _IN_MEMORY_ALERTS[alert_id].update(updates)
        col = cls._collection()
        if col is not None:
            col.update_one({"alert_id": alert_id}, {"$set": updates})
            return cls.get_by_id(alert_id)
        return _IN_MEMORY_ALERTS.get(alert_id)

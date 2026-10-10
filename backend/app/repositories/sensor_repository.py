"""Sensor Readings Repository for MongoDB."""

from typing import Optional
from app.db.collection_names import SENSOR_READINGS_COLLECTION
from app.db.mongo import get_db

_IN_MEMORY_READINGS: list[dict] = []


class SensorRepository:
    @staticmethod
    def _collection():
        db = get_db()
        return db[SENSOR_READINGS_COLLECTION] if db is not None else None

    @classmethod
    def insert(cls, reading: dict) -> dict:
        _IN_MEMORY_READINGS.append(reading.copy())
        col = cls._collection()
        if col is not None:
            col.insert_one(reading.copy())
        return reading

    @classmethod
    def get_latest_for_batch(cls, batch_id: str) -> Optional[dict]:
        col = cls._collection()
        if col is not None:
            doc = col.find_one({"batch_id": batch_id}, sort=[("timestamp", -1)])
            if doc:
                doc.pop("_id", None)
                return doc
        batch_readings = [r for r in _IN_MEMORY_READINGS if r["batch_id"] == batch_id]
        if batch_readings:
            return sorted(batch_readings, key=lambda x: x["timestamp"], reverse=True)[0]
        return None

    @classmethod
    def list_for_batch(cls, batch_id: str, limit: int = 100) -> list[dict]:
        col = cls._collection()
        if col is not None:
            docs = list(col.find({"batch_id": batch_id}).sort("timestamp", -1).limit(limit))
            if docs:
                for d in docs:
                    d.pop("_id", None)
                return docs
        batch_readings = [r for r in _IN_MEMORY_READINGS if r["batch_id"] == batch_id]
        return sorted(batch_readings, key=lambda x: x["timestamp"], reverse=True)[:limit]

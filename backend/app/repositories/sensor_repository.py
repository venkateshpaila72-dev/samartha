"""Sensor Readings Repository for MongoDB with isolated test storage."""

from typing import Optional
from fastapi import HTTPException, status
from app.core.config import settings
from app.db.collection_names import SENSOR_READINGS_COLLECTION
from app.db.mongo import get_db

_IN_MEMORY_READINGS: list[dict] = []


class SensorRepository:
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
        return db[SENSOR_READINGS_COLLECTION]

    @classmethod
    def insert(cls, reading: dict) -> dict:
        if cls._is_test():
            _IN_MEMORY_READINGS.append(reading.copy())
            return reading

        col = cls._collection()
        col.insert_one(reading.copy())
        return reading

    @classmethod
    def get_latest_for_batch(cls, batch_id: str) -> Optional[dict]:
        if cls._is_test():
            batch_readings = [r for r in _IN_MEMORY_READINGS if r["batch_id"] == batch_id]
            if batch_readings:
                return sorted(batch_readings, key=lambda x: x["timestamp"], reverse=True)[0]
            return None

        col = cls._collection()
        doc = col.find_one({"batch_id": batch_id}, sort=[("timestamp", -1)])
        if doc:
            doc.pop("_id", None)
        return doc

    @classmethod
    def list_for_batch(cls, batch_id: str, limit: int = 100) -> list[dict]:
        if cls._is_test():
            batch_readings = [r for r in _IN_MEMORY_READINGS if r["batch_id"] == batch_id]
            return sorted(batch_readings, key=lambda x: x["timestamp"], reverse=True)[:limit]

        col = cls._collection()
        docs = list(col.find({"batch_id": batch_id}).sort("timestamp", -1).limit(limit))
        for d in docs:
            d.pop("_id", None)
        return docs

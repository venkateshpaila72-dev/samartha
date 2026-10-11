"""Orchard plots and operational records for authenticated users."""
import logging, uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.api.dependencies import get_current_user
from app.db.mongo import MongoDBManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orchards", tags=["Integrated Orchard Management"])

class OrchardRecord(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    crop: str | None = Field(default=None, max_length=100)
    area_acres: float | None = Field(default=None, ge=0)
    plant_count: int | None = Field(default=None, ge=0)
    activity: str | None = Field(default=None, max_length=100)
    activity_date: str | None = Field(default=None, max_length=40)
    observation: str | None = Field(default=None, max_length=2000)
    harvest_quantity_kg: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default="kg", max_length=20)
    status: str | None = Field(default="active", max_length=40)
    notes: str | None = Field(default=None, max_length=2000)

def _collection(kind):
    db = MongoDBManager.get_database()
    if db is None: raise HTTPException(status_code=503, detail="Database is unavailable.")
    return db["orchard_" + kind]

def _owner(user):
    return str(user.get("id") or user.get("user_id") or "")

def _list(kind, user):
    try:
        docs = list(_collection(kind).find({"owner_id": _owner(user)}).sort("created_at", -1).limit(500))
        for doc in docs: doc.pop("_id", None)
        return docs
    except HTTPException: raise
    except Exception:
        logger.exception("Orchard list failed")
        raise HTTPException(status_code=500, detail="Could not load orchard records.")

def _create(kind, payload, user):
    doc = payload.model_dump()
    now = datetime.now(timezone.utc).isoformat()
    doc.update({"record_id": kind + "_" + uuid.uuid4().hex, "owner_id": _owner(user), "created_at": now, "updated_at": now})
    try:
        _collection(kind).insert_one(doc.copy())
        logger.info("Created orchard %s record %s", kind, doc["record_id"])
        return doc
    except HTTPException: raise
    except Exception:
        logger.exception("Orchard create failed")
        raise HTTPException(status_code=500, detail="Could not save orchard record.")

def _delete(kind, record_id, user):
    try:
        result = _collection(kind).delete_one({"record_id": record_id, "owner_id": _owner(user)})
        if not result.deleted_count: raise HTTPException(status_code=404, detail="Record not found.")
        logger.info("Deleted orchard %s record %s", kind, record_id)
        return {"record_id": record_id, "deleted": True}
    except HTTPException: raise
    except Exception:
        logger.exception("Orchard delete failed")
        raise HTTPException(status_code=500, detail="Could not delete orchard record.")

@router.get("/{kind}")
def list_records(kind: str, user: dict = Depends(get_current_user)):
    if kind not in {"plots", "activities", "observations", "harvests"}: raise HTTPException(status_code=404, detail="Unknown orchard record type.")
    return {"success": True, "data": _list(kind, user)}

@router.post("/{kind}")
def create_record(kind: str, payload: OrchardRecord, user: dict = Depends(get_current_user)):
    if kind not in {"plots", "activities", "observations", "harvests"}: raise HTTPException(status_code=404, detail="Unknown orchard record type.")
    return {"success": True, "data": _create(kind, payload, user)}

@router.delete("/{kind}/{record_id}")
def delete_record(kind: str, record_id: str, user: dict = Depends(get_current_user)):
    if kind not in {"plots", "activities", "observations", "harvests"}: raise HTTPException(status_code=404, detail="Unknown orchard record type.")
    return {"success": True, "data": _delete(kind, record_id, user)}

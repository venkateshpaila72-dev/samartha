"""Authenticated CRUD endpoints for restaurant and orchard operations."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.db.mongo import get_db

router = APIRouter(prefix="/operations", tags=["Restaurant & Orchard Operations"])

MODULES = {
    "menu": "restaurant_menu",
    "orders": "restaurant_orders",
    "inventory": "restaurant_inventory",
    "plots": "orchard_plots",
    "activities": "orchard_activities",
    "observations": "orchard_observations",
    "harvests": "orchard_harvests",
}

class OperationInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    status: str = Field(default="planned", max_length=40)
    notes: str = Field(default="", max_length=4000)
    quantity: float | None = None
    unit: str = Field(default="", max_length=40)
    scheduled_date: str = Field(default="", max_length=40)
    category: str = Field(default="", max_length=80)
    extra: dict[str, Any] = Field(default_factory=dict)

def _collection(module: str, user: dict):
    if module not in MODULES:
        raise HTTPException(status_code=404, detail="Unknown operations module")
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database is unavailable")
    return db[MODULES[module]], str(user["id"])

@router.get("/{module}")
async def list_operations(module: str, user: dict = Depends(get_current_user)):
    collection, user_id = _collection(module, user)
    docs = list(collection.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(500))
    return {"success": True, "data": docs}

@router.post("/{module}", status_code=status.HTTP_201_CREATED)
async def create_operation(module: str, payload: OperationInput, user: dict = Depends(get_current_user)):
    collection, user_id = _collection(module, user)
    now = datetime.now(timezone.utc).isoformat()
    doc = {"record_id": f"op_{uuid4().hex}", "module": module, "user_id": user_id,
           **payload.model_dump(), "created_at": now, "updated_at": now}
    collection.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True, "message": "Record created", "data": doc}

@router.patch("/{module}/{record_id}")
async def update_operation(module: str, record_id: str, payload: OperationInput, user: dict = Depends(get_current_user)):
    collection, user_id = _collection(module, user)
    changes = payload.model_dump()
    changes["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = collection.update_one({"record_id": record_id, "user_id": user_id}, {"$set": changes})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Record not found")
    doc = collection.find_one({"record_id": record_id, "user_id": user_id}, {"_id": 0})
    return {"success": True, "message": "Record updated", "data": doc}

@router.delete("/{module}/{record_id}")
async def delete_operation(module: str, record_id: str, user: dict = Depends(get_current_user)):
    collection, user_id = _collection(module, user)
    result = collection.delete_one({"record_id": record_id, "user_id": user_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"success": True, "message": "Record deleted"}

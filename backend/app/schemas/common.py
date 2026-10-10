"""Common Pydantic Schemas for API responses and pagination."""

from typing import Generic, Optional, TypeVar, Any
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[DataT] = None
    meta: Optional[dict[str, Any]] = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    success: bool = True
    items: list[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int


class HealthStatus(BaseModel):
    status: str = "healthy"
    database_connected: bool
    version: str = "1.0.0"
    services: dict[str, str] = Field(default_factory=dict)

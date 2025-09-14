from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class LabCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    research_domain: Optional[str] = Field(None, max_length=255)
    settings: Optional[Dict[str, Any]] = None


class LabUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    research_domain: Optional[str] = Field(None, max_length=255)
    settings: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(active|archived|suspended)$")


class LabResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    research_domain: Optional[str]
    settings: Optional[Dict[str, Any]]
    owner_id: uuid.UUID
    active_connection_id: Optional[uuid.UUID]
    active_schema_id: Optional[uuid.UUID]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LabListResponse(BaseModel):
    labs: List[LabResponse]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool


class ActivateSchemaRequest(BaseModel):
    schema_id: uuid.UUID


class ActivateConnectionRequest(BaseModel):
    connection_id: uuid.UUID

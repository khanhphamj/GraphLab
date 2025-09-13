from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    can_read: bool = Field(default=True)
    can_write: bool = Field(default=False)
    can_admin: bool = Field(default=False)
    lab_access: Optional[List[uuid.UUID]] = Field(default=None, description="List of lab IDs this key can access. None means all labs.")
    expires_at: Optional[datetime] = None


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    can_read: Optional[bool] = None
    can_write: Optional[bool] = None
    can_admin: Optional[bool] = None
    lab_access: Optional[List[uuid.UUID]] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    can_read: bool
    can_write: bool
    can_admin: bool
    lab_access: Optional[List[uuid.UUID]]
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreateResponse(BaseModel):
    """Response when creating a new API key - includes the plaintext key"""
    api_key: ApiKeyResponse
    key: str = Field(..., description="The actual API key - only shown once!")

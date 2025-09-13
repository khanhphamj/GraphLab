from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
import uuid


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    profile: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    profile: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    profile: Optional[Dict[str, Any]]
    preferences: Optional[Dict[str, Any]]
    email_verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool

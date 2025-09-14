from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class LabMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: str = Field(default="viewer", pattern="^(admin|editor|viewer)$")
    can_manage_members: bool = Field(default=False)
    can_edit_schema: bool = Field(default=False)
    can_run_jobs: bool = Field(default=False)
    can_delete_data: bool = Field(default=False)


class LabMemberUpdate(BaseModel):
    role: Optional[str] = Field(None, pattern="^(admin|editor|viewer)$")
    can_manage_members: Optional[bool] = None
    can_edit_schema: Optional[bool] = None
    can_run_jobs: Optional[bool] = None
    can_delete_data: Optional[bool] = None


class LabMemberResponse(BaseModel):
    lab_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    can_manage_members: bool
    can_edit_schema: bool
    can_run_jobs: bool
    can_delete_data: bool
    joined_at: datetime
    
    # User info for convenience
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


class LabMemberListResponse(BaseModel):
    members: List[LabMemberResponse]
    total: int

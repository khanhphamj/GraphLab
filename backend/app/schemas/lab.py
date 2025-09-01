from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid

from app.schemas.user import UserResponse

class LabBase(BaseModel):
    id: int
    name: str
    owner_id: uuid.UUID
    description: Optional[str] = None

class LabCreate(LabBase):
    pass

class LabUpdate(LabBase):
    name: Optional[str] = None
    description: Optional[str] = None

class LabResponse(LabBase):
    model_config = ConfigDict(from_attributes=True)

class LabWithOwner(LabResponse):
    owner: UserResponse
    model_config = ConfigDict(from_attributes=True)
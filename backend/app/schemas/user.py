from pydantic import BaseModel, EmailStr, constr
from typing import Optional
import uuid

# UserBase is the base model for all users
class UserBase(BaseModel):
    email: EmailStr
    name: str

# Schemas create user
class UserCreate(UserBase):
    password: constr(min_length=6)

# Schemas update user
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: uuid.UUID

    class Config:
        orm_mode = True
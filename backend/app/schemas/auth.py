from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
import uuid


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device: Optional[str] = Field(None, max_length=255)


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class EmailRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class LoginResponse(TokenResponse):
    user: "UserResponse"


class UserSessionResponse(BaseModel):
    id: uuid.UUID
    device: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_current: bool
    created_at: datetime
    last_activity: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class OAuthUrlResponse(BaseModel):
    authorization_url: str
    state: str


class OAuthAccountResponse(BaseModel):
    id: uuid.UUID
    provider: str
    provider_user_id: str
    provider_email: Optional[str]
    provider_name: Optional[str]
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Forward reference resolution
from .user import UserResponse
LoginResponse.model_rebuild()

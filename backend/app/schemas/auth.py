from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ============================================================================
# TOKEN SCHEMAS
# ============================================================================

class Token(BaseModel):
    """Basic token response"""
    access_token: str
    token_type: str = "bearer"

    class Config:
        from_attributes = True

class TokenPair(BaseModel):
    """Token pair response (access + refresh)"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until access token expires

    class Config:
        from_attributes = True

class TokenData(BaseModel):
    """Token payload data"""
    user_id: Optional[str] = None

    class Config:
        from_attributes = True

# ============================================================================
# USER AUTHENTICATION SCHEMAS
# ============================================================================

class UserLogin(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    """Registration request schema"""
    name: str
    email: EmailStr
    password: str

# ============================================================================
# TOKEN MANAGEMENT SCHEMAS
# ============================================================================

class RefreshTokenRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str

class LogoutRequest(BaseModel):
    """Logout request (optional - can use headers instead)"""
    refresh_token: Optional[str] = None

# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class UserInfo(BaseModel):
    """User information response"""
    id: str
    name: str
    email: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AuthStatus(BaseModel):
    """Authentication status response"""
    authenticated: bool
    user: Optional[UserInfo] = None

# ============================================================================
# DEBUG SCHEMAS
# ============================================================================

class TokenInfo(BaseModel):
    """Token debug information"""
    valid: bool
    expired: bool
    expires_in: int
    user_id: Optional[str] = None
    email: Optional[str] = None
    token_type: Optional[str] = None
    blacklisted: bool = False
    error: Optional[str] = None

# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Generic error response"""
    error: str
    error_code: Optional[str] = None
    details: Optional[dict] = None

class ValidationError(BaseModel):
    """Validation error response"""
    field: str
    message: str
    value: Optional[str] = None
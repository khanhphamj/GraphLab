"""Authentication routes"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.dependencies import (
    get_current_user, get_current_active_user, get_client_ip, get_user_agent
)
from app.models import User
from app.services.auth import AuthService
from app.services.api_key import ApiKeyService
from app.schemas.auth import (
    RegisterRequest, LoginRequest, LoginResponse, RefreshRequest, TokenResponse,
    ChangePasswordRequest, EmailRequest, VerifyEmailRequest,
    PasswordResetRequest, PasswordResetConfirmRequest,
    UserSessionResponse, OAuthUrlResponse, OAuthAccountResponse
)
from app.schemas.user import UserResponse
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyCreateResponse
from app.utils.exceptions import AuthenticationError, ValidationError

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Register a new user"""
    auth_service = AuthService(db)
    return await auth_service.register(request)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: Annotated[Session, Depends(get_db)]
):
    """Login user"""
    auth_service = AuthService(db)
    ip_address = get_client_ip(http_request)
    user_agent = get_user_agent(http_request)
    
    tokens, user = await auth_service.login(request, ip_address, user_agent)
    
    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user=user
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Logout current user"""
    auth_service = AuthService(db)
    
    # Get session from request state (set by dependency)
    session = getattr(request.state, 'current_session', None)
    if session:
        await auth_service.logout(session.id)
    
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Refresh access token"""
    auth_service = AuthService(db)
    return await auth_service.refresh_token(request.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get current user information"""
    return UserResponse.from_orm(current_user)


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Change password"""
    auth_service = AuthService(db)
    await auth_service.change_password(current_user.id, request)
    return {"message": "Password changed successfully"}


# Email verification
@router.post("/verify-email/send")
async def send_verification_email(
    request: EmailRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Send email verification"""
    auth_service = AuthService(db)
    await auth_service.send_verification_email(request.email)
    return {"message": "Verification email sent"}


@router.post("/verify-email/confirm")
async def verify_email(
    request: VerifyEmailRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Confirm email verification"""
    auth_service = AuthService(db)
    await auth_service.verify_email(request.token)
    return {"message": "Email verified successfully"}


# Password reset
@router.post("/password-reset/send")
async def send_password_reset(
    request: PasswordResetRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Send password reset email"""
    auth_service = AuthService(db)
    await auth_service.send_password_reset(request.email)
    return {"message": "Password reset email sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Confirm password reset"""
    auth_service = AuthService(db)
    await auth_service.confirm_password_reset(request.token, request.new_password)
    return {"message": "Password reset successfully"}


# Session management
@router.get("/sessions", response_model=List[UserSessionResponse])
async def get_user_sessions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get all user sessions"""
    auth_service = AuthService(db)
    return await auth_service.get_user_sessions(current_user.id)


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Revoke a specific session"""
    auth_service = AuthService(db)
    await auth_service.revoke_session(current_user.id, session_id)
    return {"message": "Session revoked successfully"}


# OAuth endpoints (placeholder - implement based on your OAuth provider)
@router.get("/oauth/{provider}/url", response_model=OAuthUrlResponse)
async def get_oauth_url(provider: str):
    """Get OAuth authorization URL"""
    # TODO: Implement OAuth URL generation based on provider
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth not implemented yet"
    )


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str):
    """OAuth callback endpoint"""
    # TODO: Implement OAuth callback handling
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth not implemented yet"
    )


@router.get("/oauth/accounts", response_model=List[OAuthAccountResponse])
async def get_oauth_accounts(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get linked OAuth accounts"""
    # TODO: Implement OAuth account listing
    return []


@router.delete("/oauth/accounts/{account_id}")
async def unlink_oauth_account(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Unlink OAuth account"""
    # TODO: Implement OAuth account unlinking
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth not implemented yet"
    )


# API Keys
@router.post("/api-keys", response_model=ApiKeyCreateResponse)
async def create_api_key(
    request: ApiKeyCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new API key"""
    api_key_service = ApiKeyService(db)
    return await api_key_service.create_api_key(current_user.id, request)


@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def get_api_keys(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get all API keys for current user"""
    api_key_service = ApiKeyService(db)
    return await api_key_service.get_user_api_keys(current_user.id)


@router.patch("/api-keys/{api_key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    api_key_id: uuid.UUID,
    request: ApiKeyUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update API key permissions"""
    api_key_service = ApiKeyService(db)
    return await api_key_service.update_api_key(current_user.id, api_key_id, request)


@router.delete("/api-keys/{api_key_id}")
async def revoke_api_key(
    api_key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Revoke an API key"""
    api_key_service = ApiKeyService(db)
    await api_key_service.revoke_api_key(current_user.id, api_key_id)
    return {"message": "API key revoked successfully"}

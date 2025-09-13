"""Dependencies for FastAPI routes"""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User, UserSession, ApiKey
from app.services.auth import AuthService
from app.services.api_key import ApiKeyService
from app.utils.exceptions import AuthenticationError, AuthorizationError

# Security schemes
bearer_scheme = HTTPBearer()
api_key_scheme = HTTPBearer(scheme_name="API Key")


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """Get current user from JWT token"""
    try:
        auth_service = AuthService(db)
        user, session = await auth_service.get_current_user(credentials.credentials)
        
        # Add user and session to request state for later use
        request.state.current_user = user
        request.state.current_session = session
        
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[User]:
    """Get current user from JWT token (optional)"""
    if not credentials:
        return None
    
    try:
        auth_service = AuthService(db)
        user, session = await auth_service.get_current_user(credentials.credentials)
        
        # Add user and session to request state for later use
        request.state.current_user = user
        request.state.current_session = session
        
        return user
    except AuthenticationError:
        return None


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current active user (not deleted)"""
    if current_user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )
    return current_user


async def get_current_verified_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """Get current verified user (email verified)"""
    if not current_user.email_verified_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )
    return current_user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """Require admin privileges"""
    # For now, we'll assume admin status is stored in user preferences
    # You might want to add a separate admin role system
    if not current_user.preferences or not current_user.preferences.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_api_key_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(api_key_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> tuple[User, ApiKey]:
    """Get user from API key"""
    try:
        api_key_service = ApiKeyService(db)
        api_key = await api_key_service.verify_api_key(credentials.credentials)
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        user = db.query(User).filter(User.id == api_key.user_id).first()
        if not user or user.deleted_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Add user and api_key to request state
        request.state.current_user = user
        request.state.current_api_key = api_key
        
        return user, api_key
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )


def get_client_ip(request: Request) -> Optional[str]:
    """Get client IP address from request"""
    # Check for X-Forwarded-For header (proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Check for X-Real-IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection
    if request.client:
        return request.client.host
    
    return None


def get_user_agent(request: Request) -> Optional[str]:
    """Get user agent from request"""
    return request.headers.get("User-Agent")

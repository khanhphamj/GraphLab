"""Dependencies for FastAPI routes"""

import uuid
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import get_db
from app.models import User, UserSession, ApiKey, Lab, LabMember
from app.services.auth import AuthService
from app.services.api_key import ApiKeyService
from app.services.lab import LabService
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


async def get_lab_by_id(
    lab_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
) -> Lab:
    """Get lab by ID and check user access"""
    lab_service = LabService(db)
    try:
        lab_response = await lab_service.get_lab_by_id(current_user.id, lab_id)
        # Return the actual Lab model for further use
        lab = db.query(Lab).filter(Lab.id == lab_id).first()
        return lab
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found")
        elif "access denied" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def require_lab_owner(
    lab: Annotated[Lab, Depends(get_lab_by_id)],
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> Lab:
    """Require user to be lab owner"""
    if lab.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lab owner can perform this action"
        )
    return lab


async def require_lab_admin(
    lab: Annotated[Lab, Depends(get_lab_by_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
) -> Lab:
    """Require user to be lab owner or admin member"""
    # Check if owner
    if lab.owner_id == current_user.id:
        return lab
    
    # Check if admin member
    member = db.query(LabMember).filter(
        and_(
            LabMember.lab_id == lab.id,
            LabMember.user_id == current_user.id,
            LabMember.role == 'admin'
        )
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return lab


async def require_lab_member_manager(
    lab: Annotated[Lab, Depends(get_lab_by_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
) -> Lab:
    """Require user to be lab owner or admin member with manage_members permission"""
    # Check if owner
    if lab.owner_id == current_user.id:
        return lab
    
    # Check if admin member with manage_members permission
    member = db.query(LabMember).filter(
        and_(
            LabMember.lab_id == lab.id,
            LabMember.user_id == current_user.id,
            LabMember.role == 'admin',
            LabMember.can_manage_members == True
        )
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Member management privileges required"
        )
    
    return lab

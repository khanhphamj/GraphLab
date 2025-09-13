"""User management routes (Admin endpoints)"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.dependencies import get_current_active_user, require_admin
from app.models import User
from app.services.user import UserService
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse

router = APIRouter(prefix="/v1/users", tags=["Users"])


@router.post("", response_model=UserResponse)
async def create_user(
    request: UserCreate,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new user (Admin only)"""
    user_service = UserService(db)
    return await user_service.create_user(request)


@router.get("", response_model=UserListResponse)
async def get_users(
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    q: Optional[str] = Query(None, description="Search query for name or email"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """Get list of users with search and pagination (Admin only)"""
    user_service = UserService(db)
    return await user_service.get_users(q=q, page=page, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get user by ID (Admin or own profile)"""
    user_service = UserService(db)
    
    # Check if user is admin or requesting own profile
    is_admin = current_user.preferences and current_user.preferences.get("is_admin", False)
    if not is_admin and current_user.id != user_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return await user_service.get_user_by_id(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    request: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update user profile/preferences (Admin or own profile)"""
    user_service = UserService(db)
    
    # Check if user is admin or updating own profile
    is_admin = current_user.preferences and current_user.preferences.get("is_admin", False)
    if not is_admin and current_user.id != user_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return await user_service.update_user(user_id, request)


@router.delete("/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    """Soft delete user (Admin only)"""
    user_service = UserService(db)
    await user_service.delete_user(user_id)
    return {"message": "User deleted successfully"}

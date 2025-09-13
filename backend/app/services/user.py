from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import uuid

from app.models import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.utils.auth import hash_password
from app.utils.exceptions import NotFoundError, ConflictError


class UserService:
    def __init__(self, db: Session):
        self.db = db

    async def create_user(self, request: UserCreate) -> UserResponse:
        """Create a new user (Admin only)"""
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise ConflictError("User with this email already exists")

        # Create new user
        user = User(
            name=request.name,
            email=request.email,
            hashed_password=hash_password(request.password),
            profile=request.profile,
            preferences=request.preferences
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return UserResponse.from_orm(user)

    async def get_users(
        self, 
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> UserListResponse:
        """Get list of users with search and pagination"""
        query = self.db.query(User).filter(User.deleted_at.is_(None))

        # Search filter
        if q:
            search_filter = or_(
                User.name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%")
            )
            query = query.filter(search_filter)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * limit
        users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

        # Calculate pagination info
        has_next = offset + limit < total
        has_prev = page > 1

        return UserListResponse(
            users=[UserResponse.from_orm(user) for user in users],
            total=total,
            page=page,
            limit=limit,
            has_next=has_next,
            has_prev=has_prev
        )

    async def get_user_by_id(self, user_id: uuid.UUID) -> UserResponse:
        """Get user by ID"""
        user = self.db.query(User).filter(
            and_(User.id == user_id, User.deleted_at.is_(None))
        ).first()
        
        if not user:
            raise NotFoundError("User not found")

        return UserResponse.from_orm(user)

    async def update_user(self, user_id: uuid.UUID, request: UserUpdate) -> UserResponse:
        """Update user profile/preferences"""
        user = self.db.query(User).filter(
            and_(User.id == user_id, User.deleted_at.is_(None))
        ).first()
        
        if not user:
            raise NotFoundError("User not found")

        # Update fields
        if request.name is not None:
            user.name = request.name
        if request.profile is not None:
            user.profile = request.profile
        if request.preferences is not None:
            user.preferences = request.preferences

        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)

        return UserResponse.from_orm(user)

    async def delete_user(self, user_id: uuid.UUID) -> None:
        """Soft delete user (Admin only)"""
        user = self.db.query(User).filter(
            and_(User.id == user_id, User.deleted_at.is_(None))
        ).first()
        
        if not user:
            raise NotFoundError("User not found")

        # Soft delete
        user.deleted_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email (internal use)"""
        return self.db.query(User).filter(
            and_(User.email == email, User.deleted_at.is_(None))
        ).first()

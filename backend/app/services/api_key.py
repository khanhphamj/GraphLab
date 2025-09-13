from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid

from app.models import ApiKey, User
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyCreateResponse
from app.utils.auth import generate_api_key, hash_api_key
from app.utils.exceptions import NotFoundError


class ApiKeyService:
    def __init__(self, db: Session):
        self.db = db

    async def create_api_key(self, user_id: uuid.UUID, request: ApiKeyCreate) -> ApiKeyCreateResponse:
        """Create a new API key"""
        # Generate the actual key
        key = generate_api_key()
        key_hash = hash_api_key(key)

        # Create API key record
        api_key = ApiKey(
            user_id=user_id,
            name=request.name,
            key_hash=key_hash,
            can_read=request.can_read,
            can_write=request.can_write,
            can_admin=request.can_admin,
            lab_access={"lab_ids": request.lab_access} if request.lab_access else None,
            expires_at=request.expires_at
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        return ApiKeyCreateResponse(
            api_key=ApiKeyResponse.from_orm(api_key),
            key=key  # Only shown once!
        )

    async def get_user_api_keys(self, user_id: uuid.UUID) -> List[ApiKeyResponse]:
        """Get all API keys for a user"""
        api_keys = self.db.query(ApiKey).filter(
            and_(
                ApiKey.user_id == user_id,
                ApiKey.revoked_at.is_(None)
            )
        ).order_by(ApiKey.created_at.desc()).all()

        return [ApiKeyResponse.from_orm(key) for key in api_keys]

    async def update_api_key(
        self, 
        user_id: uuid.UUID, 
        api_key_id: uuid.UUID, 
        request: ApiKeyUpdate
    ) -> ApiKeyResponse:
        """Update API key permissions"""
        api_key = self.db.query(ApiKey).filter(
            and_(
                ApiKey.id == api_key_id,
                ApiKey.user_id == user_id,
                ApiKey.revoked_at.is_(None)
            )
        ).first()

        if not api_key:
            raise NotFoundError("API key not found")

        # Update fields
        if request.name is not None:
            api_key.name = request.name
        if request.can_read is not None:
            api_key.can_read = request.can_read
        if request.can_write is not None:
            api_key.can_write = request.can_write
        if request.can_admin is not None:
            api_key.can_admin = request.can_admin
        if request.lab_access is not None:
            api_key.lab_access = {"lab_ids": request.lab_access} if request.lab_access else None
        if request.is_active is not None:
            api_key.is_active = request.is_active
        if request.expires_at is not None:
            api_key.expires_at = request.expires_at

        self.db.commit()
        self.db.refresh(api_key)

        return ApiKeyResponse.from_orm(api_key)

    async def revoke_api_key(self, user_id: uuid.UUID, api_key_id: uuid.UUID) -> None:
        """Revoke an API key"""
        api_key = self.db.query(ApiKey).filter(
            and_(
                ApiKey.id == api_key_id,
                ApiKey.user_id == user_id,
                ApiKey.revoked_at.is_(None)
            )
        ).first()

        if not api_key:
            raise NotFoundError("API key not found")

        api_key.is_active = False
        api_key.revoked_at = datetime.now(timezone.utc)
        self.db.commit()

    async def verify_api_key(self, key: str) -> Optional[ApiKey]:
        """Verify an API key and return the API key record"""
        key_hash = hash_api_key(key)
        
        api_key = self.db.query(ApiKey).filter(
            and_(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,
                ApiKey.revoked_at.is_(None),
                or_(
                    ApiKey.expires_at.is_(None),
                    ApiKey.expires_at > datetime.now(timezone.utc)
                )
            )
        ).first()

        if api_key:
            # Update last used timestamp
            api_key.last_used_at = datetime.now(timezone.utc)
            self.db.commit()

        return api_key

    async def get_api_key_by_id(self, user_id: uuid.UUID, api_key_id: uuid.UUID) -> ApiKeyResponse:
        """Get specific API key by ID"""
        api_key = self.db.query(ApiKey).filter(
            and_(
                ApiKey.id == api_key_id,
                ApiKey.user_id == user_id,
                ApiKey.revoked_at.is_(None)
            )
        ).first()

        if not api_key:
            raise NotFoundError("API key not found")

        return ApiKeyResponse.from_orm(api_key)

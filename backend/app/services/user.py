from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
import uuid
from typing import Optional
from app.core.security import get_password_hash
from datetime import datetime, timezone
from app.core.validators import validate_email, validate_password, validate_name
import logging

logger = logging.getLogger(__name__)

class UserServiceError(Exception):
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details
        self.timestamp = datetime.now(timezone.utc)

class EmailAlreadyExistsError(UserServiceError):
    def __init__(self, email: str):
        super().__init__(
            f"Email {email} already exists",
            error_code="EMAIL_ALREADY_EXISTS",
            details={"email": email}
            )

class NameAlreadyExistsError(UserServiceError):
    def __init__(self, name: str):
        super().__init__(
            f"Name {name} already exists",
            error_code="NAME_ALREADY_EXISTS",
            details={"name": name}
            )
            
class UserNotFoundError(UserServiceError):
    def __init__(self, identifier):
        super().__init__(
            f"User with identifier {identifier} not found",
            error_code="USER_NOT_FOUND",
            details={"identifier": identifier}
            )

class InvalidEmailError(UserServiceError):
    def __init__(self, email: str):
        super().__init__(
            f"Invalid email: {email}",
            error_code="INVALID_EMAIL",
            details={"email": email}
            )
                
class InvalidPasswordError(UserServiceError):
    def __init__(self, password: str):
        super().__init__(
            f"Invalid password",
            error_code="INVALID_PASSWORD"
            )

# Helper functions
def _active_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(
        User.email == email,
        User.deleted_at.is_(None)
        ).first()
    
def _active_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
        ).first()

def _active_by_name(db: Session, user_name: str) -> Optional[User]:
    return db.query(User).filter(
        User.name == user_name,
        User.deleted_at.is_(None)
        ).first()

#Service functions
def create_user(db: Session, user_in: UserCreate) -> UserResponse:
    try:
        #Validate name
        validate_name(user_in.name)
        #Validate email
        validate_email(user_in.email)
        existing_user = _active_by_email(db, user_in.email)
        if existing_user:
            logger.warning(f"Email {user_in.email} already exists")
            raise EmailAlreadyExistsError(user_in.email)
        #Validate password
        validate_password(user_in.password)
        db_user = User(
            name=user_in.name,
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User {db_user.id}, email {db_user.email} created successfully")
        return UserResponse.model_validate(db_user)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        db.rollback()
        raise

def get_user(db: Session, user_id: uuid.UUID = None, email: str = None, name: str = None) -> UserResponse:
    if user_id is not None:
        user = _active_by_id(db, user_id)
    elif email is not None:
        user = _active_by_email(db, email)
    elif name is not None:
        user = _active_by_name(db, name)
    else:
        logger.warning("No identifier provided")
        raise ValueError("At least one identifier (user_id, email, name) must be provided")
    if not user:
        identifier = str(user_id) if user_id else (email or name)
        logger.warning(f"User not found with identifier {identifier}")
        raise UserNotFoundError(identifier)
    return UserResponse.model_validate(user)

def get_user_model(db: Session, user_id: uuid.UUID = None, email: str = None, name: str = None) -> User:
    if user_id is not None:
        return _active_by_id(db, user_id)
    elif email is not None:
        return _active_by_email(db, email)
    elif name is not None:
        return _active_by_name(db, name)
    else:
        logger.warning("No identifier provided")
        raise ValueError("At least one identifier (user_id, email, name) must be provided")
    return user

def update_user(db: Session, user_id: uuid.UUID, user_in: UserUpdate) -> UserResponse:
    user = _active_by_id(db, user_id)
    if not user:
        logger.warning(f"User {user_id} not found")
        raise UserNotFoundError(user_id)    
    if user_in.name:
        validate_name(user_in.name)
        existing_user = _active_by_name(db, user_in.name)
        if existing_user and existing_user.id != user_id:
            raise NameAlreadyExistsError(user_in.name)
        user.name = user_in.name
    #Validate email
    if user_in.email:
        validate_email(user_in.email)
        existing_user = _active_by_email(db, user_in.email)
        if existing_user and existing_user.id != user_id:
            raise EmailAlreadyExistsError(user_in.email)
        user.email = user_in.email
    #Validate password
    if user_in.password:
        validate_password(user_in.password)
        user.hashed_password = get_password_hash(user_in.password)
    try:
        db.commit()
        db.refresh(user)
        logger.info(f"User {user_id} updated successfully")
        return UserResponse.model_validate(user)
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        db.rollback()
        raise

def delete_user(db: Session, user_id: uuid.UUID) -> None:
    user = _active_by_id(db, user_id)
    if not user:
        logger.warning(f"User {user_id} not found")
        raise UserNotFoundError(user_id)
    user.deleted_at = datetime.now(timezone.utc)
    try:
        db.commit()
        logger.info(f"User {user_id} deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        db.rollback()
        raise
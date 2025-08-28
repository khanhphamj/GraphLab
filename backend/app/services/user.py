from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserRead
import uuid
from typing import Optional
from app.utils.hash import get_password_hash, verify_password
from datetime import datetime, timezone
from app.core.validators import validate_email, validate_password
import logging
import re

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
        

class UserNotFoundError(UserServiceError):
    def __init__(self, user_id: int):
        super().__init__(
            f"User with id {user_id} not found",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id}
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
        User.deleted_at == None
        ).first()
    
def _active_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.query(User).filter(
        User.id == user_id,
        User.deleted_at == None
        ).first()

def _active_by_name(db: Session, name: str) -> Optional[User]:
    return db.query(User).filter(
        User.name == name,
        User.deleted_at == None
        ).first()


#Service functions
def create_user(db: Session, user_in: UserCreate) -> User:
    #Validate email
    validate_email(user_in.email)

    #Check if user already exists
    if _active_by_email(db, user_in.email):
        raise EmailAlreadyExistsError(user_in.email)
    
    #Validate password
    validate_password(user_in.password)

    #Create user
    db_user = User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        )
    
    #Add user to database
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

def get_user(db: Session, user_id: uuid.UUID = None, email: str = None, name: str = None) -> User:
    if user_id is not None:
        user = _active_by_id(db, user_id)
    elif email is not None:
        user = _active_by_email(db, email)
    elif name is not None:
        user = db.query(User).filter(
            User.name == name,
            User.deleted_at == None
        ).first()
    else:
        raise ValueError("At least one identifier (user_id, email, name) must be provided")
    
    if not user:
        raise UserNotFoundError(user_id or email or name)
    return user

def update_user(db: Session, user_id: uuid.UUID, user_in: UserUpdate) -> User:
    user = _active_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(user_id)
    
    if user_in.name:
        user.name = user_in.name
    if user_in.email:
        user.email = user_in.email
    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)
    
    #Update user
    db.commit()
    db.refresh(user)

    return user

def delete_user(db: Session, user_id: uuid.UUID) -> None:
    user = _active_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(user_id)
    
    user.deleted_at = datetime.now(timezone.utc)
    db.commit()
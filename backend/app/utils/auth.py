import os
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from passlib.context import CryptContext
from jose import JWTError, jwt
from .exceptions import AuthenticationError

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings - should come from environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
VERIFICATION_TOKEN_EXPIRE_HOURS = int(os.getenv("VERIFICATION_TOKEN_EXPIRE_HOURS", "24"))


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password_hash(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


# Aliases for backward compatibility
hash_password = get_password_hash
verify_password = verify_password_hash


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        
        if token_type != expected_type:
            raise AuthenticationError(f"Invalid token type. Expected {expected_type}, got {token_type}")
        
        # Check expiration
        exp = payload.get("exp")
        if exp is None:
            raise AuthenticationError("Token missing expiration")
        
        if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise AuthenticationError("Token expired")
        
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


def generate_verification_token(email: str, purpose: str = "email_verify") -> str:
    """Generate a verification token for email verification or password reset"""
    data = {
        "email": email,
        "purpose": purpose,
        "exp": datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def verify_verification_token(token: str, expected_purpose: str = "email_verify") -> str:
    """Verify a verification token and return the email"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("email")
        purpose = payload.get("purpose")
        
        if not email:
            raise AuthenticationError("Invalid token: missing email")
        
        if purpose != expected_purpose:
            raise AuthenticationError(f"Invalid token purpose. Expected {expected_purpose}, got {purpose}")
        
        # Check expiration
        exp = payload.get("exp")
        if exp is None:
            raise AuthenticationError("Token missing expiration")
        
        if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise AuthenticationError("Token expired")
        
        return email
    except JWTError as e:
        raise AuthenticationError(f"Invalid verification token: {str(e)}")


def generate_api_key() -> str:
    """Generate a secure API key"""
    # Generate 32 random bytes and encode as hex
    return secrets.token_hex(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash"""
    return hmac.compare_digest(hash_api_key(api_key), hashed_key)

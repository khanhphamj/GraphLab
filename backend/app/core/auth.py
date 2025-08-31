from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Set
from jose import JWTError, jwt
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY is not set")

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

def validate_config():
    if len(SECRET_KEY) < 32:
        raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
    if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
        raise ValueError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")
    if REFRESH_TOKEN_EXPIRE_DAYS <= 0:
        raise ValueError("JWT_REFRESH_TOKEN_EXPIRE_DAYS must be greater than 0")

validate_config()
blacklisted_tokens: Set[str] = set()

def blacklist_token(token: str) -> bool:
    try:
        blacklisted_tokens.add(token)
        logger.info(f"Token blacklisted successfully")
        return True
    except Exception as e:
        logger.error(f"Error blacklisting token: {e}")
        return False

def is_token_blacklisted(token: str) -> bool:
    return token in blacklisted_tokens

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)) -> str:
    try:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({
            "exp": expire, 
            "iat": datetime.now(timezone.utc),
            "type": "access"
            })
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Access token created successfully")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise

def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)) -> str:
    try:
        if expires_delta is None:
            expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode = data.copy()
        to_encode.update({
            "exp": expire, 
            "iat": datetime.now(timezone.utc),
            "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Refresh token created successfully")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise

def create_token_pair(user_id: str, user_email: str) -> Dict[str, str]:
    try:
        token_data = {
            "user_id": user_id,
            "user_email": user_email
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        logger.info(f"Token pair created successfully")
        return {
            "access_token": access_token, 
            "refresh_token": refresh_token, 
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
    except Exception as e:
        logger.error(f"Error creating token pair: {e}")
        raise

def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    try:
        if is_token_blacklisted(token):
            raise JWTError("Token is blacklisted")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != token_type:
            raise JWTError("Invalid token type")

        return payload
    
    except JWTError as e:
        logger.error(f"Error verifying token: {e}")
        raise

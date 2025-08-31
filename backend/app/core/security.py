from passlib.context import CryptContext
import logging
from typing import Optional

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if not plain_password or not hashed_password:
            logger.warning("Empty password or hashed password")
            return False

        result = pwd_context.verify(plain_password, hashed_password)
        logger.info(f"Password verification completed")
        return result
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False
    
def get_password_hash(password: str) -> str:
    """Hash password using passlib context."""
    try:
        if not password or not isinstance(password, str):
            raise ValueError("Password must be a non-empty string")
        
        if len(password.strip()) == 0:
            raise ValueError("Password cannot be empty or whitespace only")
        
        hashed = pwd_context.hash(password)
        logger.info("Password hashing completed")
        return hashed
        
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise ValueError(f"Failed to hash password: {str(e)}")
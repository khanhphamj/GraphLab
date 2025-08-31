from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.models.user import User
from app.db.deps import get_db
from app.core.auth import create_token_pair, verify_token, blacklist_token, is_token_blacklisted
from app.core.security import verify_password
from app.services.user import get_user_model, get_user
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# FASTAPI SECURITY SCHEME
# ============================================================================

security = HTTPBearer()

# ============================================================================
# FASTAPI DEPENDENCIES - FRAMEWORK SPECIFIC
# ============================================================================

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                    db: Session = Depends(get_db)) -> User:
    """
    FastAPI dependency để lấy current authenticated user từ JWT token.
    
    Usage:
        @app.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.name}
    
    Raises:
        HTTPException: 401 nếu token invalid hoặc user không tồn tại
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials or not credentials.credentials:
        logger.warning("No credentials provided")
        raise credentials_exception
    
    token = credentials.credentials
    
    try:
        # Verify token with core function
        payload = verify_token(token, "access")
        
        user_id = payload.get("user_id")
        if user_id is None:
            logger.warning("Token missing user_id")
            raise credentials_exception

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise credentials_exception

    try:
        # Get user from database
        user = get_user(db, user_id=user_id)
        if not user:
            logger.warning(f"User {user_id} not found in database")
            raise credentials_exception
            
        logger.info(f"User {user_id} authenticated successfully")
        return user

    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {e}")
        raise credentials_exception

def get_current_active_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication dependency.
    
    Trả về User nếu có token hợp lệ, None nếu không.
    Không raise exception, phù hợp cho optional authentication.
    
    Usage:
        @app.get("/public")
        def public_route(user: Optional[User] = Depends(get_current_active_user_optional)):
            if user:
                return {"message": f"Hello {user.name}"}
            return {"message": "Hello anonymous"}
    """
    if not credentials or not credentials.credentials:
        return None
    
    token = credentials.credentials
    
    try:
        payload = verify_token(token, "access")
        
        user_id = payload.get("user_id")
        if user_id:
            user = get_user(db, user_id=user_id)
            return user
    except Exception as e:
        logger.debug(f"Token validation failed: {e}")
        return None
    
    return None

# ============================================================================
# AUTHENTICATION BUSINESS LOGIC - APPLICATION SPECIFIC
# ============================================================================

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate user với email và password.
    
    Business logic:
    - Tìm user theo email
    - Verify password hash
    - Trả về User object nếu thành công
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
        
    Returns:
        User object nếu authentication thành công, None nếu thất bại
    """
    try:
        # Validate input
        if not email or not password:
            logger.warning("Empty email or password provided")
            return None
            
        # Find user by email
        user = get_user_model(db, email=email)
        if not user:
            logger.warning(f"Authentication failed: User not found with email {email}")
            return None
        
        # Verify password using core function
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password for user {email}")
            return None
        
        logger.info(f"User {email} authenticated successfully")
        return user
        
    except Exception as e:
        logger.error(f"Error during user authentication for {email}: {e}")
        return None

def login_user(db: Session, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Login user và trả về token pair.
    
    Business workflow:
    1. Authenticate user với credentials
    2. Tạo access và refresh tokens
    3. Trả về token pair
    
    Args:
        db: Database session
        email: User email  
        password: Plain text password
        
    Returns:
        Dict chứa access_token, refresh_token, etc. nếu thành công
        None nếu authentication thất bại
    """
    try:
        # Step 1: Authenticate user
        user = authenticate_user(db, email, password)
        if not user:
            logger.warning(f"Login failed for email: {email}")
            return None
        
        # Step 2: Create token pair using core function
        tokens = create_token_pair(str(user.id), user.email)
        
        # Optional: Update last login timestamp
        # user.last_login_at = datetime.now(timezone.utc)
        # db.commit()
        
        logger.info(f"User {email} logged in successfully")
        return tokens
        
    except Exception as e:
        logger.error(f"Error during login for {email}: {e}")
        return None

def refresh_access_token(refresh_token: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Refresh access token sử dụng refresh token.
    
    Business workflow:
    1. Validate refresh token
    2. Verify user vẫn tồn tại trong database
    3. Tạo token pair mới
    4. Blacklist old refresh token (optional)
    
    Args:
        refresh_token: JWT refresh token
        db: Database session
        
    Returns:
        New token pair nếu thành công, None nếu thất bại
    """
    try:
        # Step 1: Check if refresh token is blacklisted
        if is_token_blacklisted(refresh_token):
            logger.warning("Attempt to use blacklisted refresh token")
            return None
        
        # Step 2: Verify refresh token
        payload = verify_token(refresh_token, "refresh")
        
        user_id = payload.get("user_id")
        user_email = payload.get("user_email")
        
        if not user_id:
            logger.warning("Refresh token missing user_id")
            return None
        
        # Step 3: Verify user still exists
        user = get_user(db, user_id=user_id)
        if not user:
            logger.warning(f"User {user_id} no longer exists during token refresh")
            return None
        
        # Step 4: Create new token pair
        new_tokens = create_token_pair(user_id, user_email)
        
        # Optional: Blacklist old refresh token to prevent reuse
        # blacklist_token(refresh_token)
        
        logger.info(f"Refreshed tokens for user {user_id}")
        return new_tokens
        
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return None

def logout_user(access_token: str, refresh_token: str = None) -> bool:
    """
    Logout user bằng cách blacklist tokens.
    
    Business workflow:
    1. Blacklist access token
    2. Blacklist refresh token (nếu có)
    3. Return success status
    
    Args:
        access_token: JWT access token
        refresh_token: Optional JWT refresh token
        
    Returns:
        True nếu logout thành công, False nếu có lỗi
    """
    try:
        # Step 1: Blacklist access token
        access_blacklisted = blacklist_token(access_token)
        
        # Step 2: Blacklist refresh token if provided
        refresh_blacklisted = blacklist_token(refresh_token) if refresh_token else True
        
        if access_blacklisted and refresh_blacklisted:
            logger.info("User logged out successfully")
            return True
        else:
            logger.error("Failed to blacklist tokens during logout")
            return False
            
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return False

# ============================================================================
# ADDITIONAL UTILITY FUNCTIONS
# ============================================================================

def validate_user_credentials(db: Session, email: str, password: str) -> Dict[str, Any]:
    """
    Validate user credentials và trả về detailed information.
    
    Useful cho API responses với detailed error information.
    
    Returns:
        Dict với validation results và error details
    """
    try:
        result = {
            "is_valid": False,
            "user_exists": False,
            "password_valid": False,
            "user": None,
            "errors": []
        }
        
        # Check if email is provided
        if not email:
            result["errors"].append("Email is required")
            return result
            
        # Check if password is provided
        if not password:
            result["errors"].append("Password is required")
            return result
        
        # Find user by email
        user = get_user(db, email=email)
        
        if not user:
            result["errors"].append("User not found")
            return result
        
        result["user_exists"] = True
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            result["errors"].append("Invalid password")
            return result
        
        result["is_valid"] = True
        result["password_valid"] = True
        result["user"] = user
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating credentials for {email}: {e}")
        return {
            "is_valid": False,
            "user_exists": False,
            "password_valid": False,
            "user": None,
            "errors": [f"Validation error: {str(e)}"]
        }

def get_user_from_token(token: str, db: Session) -> Optional[User]:
    """
    Lấy user từ JWT token mà không raise exception.
    
    Useful cho internal functions.
    
    Args:
        token: JWT token
        db: Database session
        
    Returns:
        User object nếu token hợp lệ, None nếu không
    """
    try:
        payload = verify_token(token, "access")
        user_id = payload.get("user_id")
        
        if user_id:
            user = get_user(db, user_id=user_id)
            return user
            
    except Exception as e:
        logger.debug(f"Error getting user from token: {e}")
        return None
    
    return None

def get_token_info(token: str) -> Dict[str, Any]:
    """
    Get detailed token information for debugging purposes.
    
    Returns token analysis including validity, expiration, user info, etc.
    """
    from app.schemas.auth import TokenInfo
    
    try:
        # Check if token is blacklisted
        blacklisted = is_token_blacklisted(token)
        if blacklisted:
            return TokenInfo(
                valid=False,
                expired=False,
                expires_in=0,
                blacklisted=True,
                error="Token is blacklisted"
            ).model_dump()
        
        # Try to verify token
        try:
            payload = verify_token(token, "access")
            
            # Calculate expiration time
            exp_timestamp = payload.get("exp")
            current_time = datetime.now(timezone.utc).timestamp()
            
            if exp_timestamp:
                expires_in = max(0, int(exp_timestamp - current_time))
                expired = expires_in == 0
            else:
                expires_in = 0
                expired = True
            
            return TokenInfo(
                valid=not expired,
                expired=expired,
                expires_in=expires_in,
                user_id=payload.get("user_id"),
                email=payload.get("user_email"),
                token_type=payload.get("type"),
                blacklisted=False
            ).model_dump()
            
        except Exception as e:
            # Token is invalid
            return TokenInfo(
                valid=False,
                expired=False,
                expires_in=0,
                blacklisted=False,
                error=str(e)
            ).model_dump()
            
    except Exception as e:
        logger.error(f"Error analyzing token: {e}")
        return TokenInfo(
            valid=False,
            expired=False,
            expires_in=0,
            blacklisted=False,
            error=f"Analysis error: {str(e)}"
        ).model_dump()
    return None

# ============================================================================
# CUSTOM EXCEPTIONS - APPLICATION SPECIFIC
# ============================================================================

class AuthServiceError(Exception):
    """Base exception cho Auth Service"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)

class InvalidCredentialsError(AuthServiceError):
    """Exception cho invalid credentials"""
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(
            message,
            error_code="INVALID_CREDENTIALS",
            details={"message": "The provided credentials are incorrect"}
        )

class UserNotFoundError(AuthServiceError):
    """Exception khi user không tồn tại"""
    def __init__(self, identifier: str):
        super().__init__(
            f"User not found: {identifier}",
            error_code="USER_NOT_FOUND",
            details={"identifier": identifier}
        )

class TokenExpiredError(AuthServiceError):
    """Exception khi token đã expire"""
    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            message,
            error_code="TOKEN_EXPIRED",
            details={"message": "Please refresh your token or login again"}
        )

class TokenBlacklistedError(AuthServiceError):
    """Exception khi token đã bị blacklist"""
    def __init__(self, message: str = "Token has been revoked"):
        super().__init__(
            message,
            error_code="TOKEN_BLACKLISTED",
            details={"message": "This token is no longer valid"}
        )
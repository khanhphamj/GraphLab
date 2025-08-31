from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.schemas.auth import UserLogin, UserRegister, TokenPair, RefreshTokenRequest, TokenInfo
from app.services.auth import login_user, logout_user, refresh_access_token, get_current_user, get_current_active_user_optional
from app.services.user import create_user
from app.db.deps import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["authentication"])

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    User registration endpoint.
    
    - Validates user data
    - Creates new user in database
    - Returns authentication tokens
    """
    try:
        # Import user creation function
        from app.schemas.user import UserCreate
        
        # Convert to UserCreate schema
        user_create = UserCreate(
            name=user_data.name,
            email=user_data.email,
            password=user_data.password
        )
        
        # Create user using user service
        new_user = create_user(db, user_create)
        
        # Auto-login after registration
        tokens = login_user(db, user_data.email, user_data.password)
        
        if not tokens:
            # This shouldn't happen, but handle just in case
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration successful but login failed"
            )
        
        return tokens
        
    except Exception as e:
        # Handle specific errors
        error_msg = str(e)
        if "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        elif "password" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid password format"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: {error_msg}"
            )

@router.post("/login", response_model=TokenPair)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    User login endpoint.
    
    - Validates credentials
    - Returns authentication tokens
    """
    try:
        tokens = login_user(db, login_data.email, login_data.password)
        
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/refresh", response_model=TokenPair)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Token refresh endpoint.
    
    - Validates refresh token
    - Returns new token pair
    """
    try:
        new_tokens = refresh_access_token(request.refresh_token, db)
        
        if not new_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return new_tokens
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    current_user: User = Depends(get_current_user),
    refresh_token: str = None,
    request: Request = None
):
    """
    User logout endpoint - SECURE.
    
    - Gets access token from Authorization header
    - Blacklists both access and refresh tokens
    - Returns success message
    """
    try:
        # Extract access token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        access_token = auth_header.replace("Bearer ", "")
        
        # Logout user with extracted tokens
        success = logout_user(access_token, refresh_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )
        
        return {"message": "Successfully logged out"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout error: {str(e)}"
        )
        
# ============================================================================
# USER INFO ENDPOINTS
# ============================================================================

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    - Requires valid access token
    - Returns user details
    """
    try:
        return {
            "id": str(current_user.id),
            "name": current_user.name,
            "email": current_user.email,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )

@router.get("/verify")
def verify_token_status(current_user: User = Depends(get_current_active_user_optional)):
    """
    Verify token status.
    
    - Optional authentication
    - Returns authentication status
    """
    if current_user:
        return {
            "authenticated": True,
            "user": {
                "id": str(current_user.id),
                "name": current_user.name,
                "email": current_user.email
            }
        }
    else:
        return {
            "authenticated": False,
            "user": None
        }

# ============================================================================
# DEBUG ENDPOINTS (REMOVE IN PRODUCTION)
# ============================================================================

@router.get("/debug/token/{token}", response_model=TokenInfo)
def debug_token_info(token: str):
    """
    Debug endpoint to inspect token information.
    
    ⚠️ REMOVE THIS ENDPOINT IN PRODUCTION ⚠️
    Only for development and debugging purposes.
    """
    try:
        from app.services.auth import get_token_info
        return get_token_info(token)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token inspection failed: {str(e)}"
        )
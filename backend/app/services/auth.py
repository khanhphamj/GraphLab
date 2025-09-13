from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid

from app.models import User, UserSession, UserVerification
from app.schemas.auth import (
    RegisterRequest, LoginRequest, ChangePasswordRequest,
    TokenResponse, UserSessionResponse
)
from app.schemas.user import UserResponse
from app.utils.auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    verify_token, generate_verification_token, verify_verification_token,
    hash_api_key
)
from app.utils.email import send_verification_email, send_password_reset_email
from app.utils.exceptions import (
    AuthenticationError, ConflictError, NotFoundError, ValidationError
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    async def register(self, request: RegisterRequest) -> UserResponse:
        """Register a new user"""
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise ConflictError("User with this email already exists")

        # Create new user
        user = User(
            name=request.name,
            email=request.email,
            hashed_password=hash_password(request.password)
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Send verification email
        await self.send_verification_email(request.email)

        return UserResponse.from_orm(user)

    async def login(
        self, 
        request: LoginRequest, 
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[TokenResponse, UserResponse]:
        """Login user and create session"""
        # Find user
        user = self.db.query(User).filter(
            and_(User.email == request.email, User.deleted_at.is_(None))
        ).first()
        
        if not user or not verify_password(request.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        # Create session
        session = await self._create_user_session(
            user.id, 
            device=request.device,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Create tokens
        token_data = {"sub": str(user.id), "session_id": str(session.id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Update session with refresh token hash
        session.refresh_token_hash = hash_api_key(refresh_token)
        self.db.commit()

        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60  # 30 minutes
        )

        return tokens, UserResponse.from_orm(user)

    async def logout(self, session_id: uuid.UUID) -> None:
        """Logout user by revoking session"""
        session = self.db.query(UserSession).filter(UserSession.id == session_id).first()
        if session:
            session.is_active = False
            session.revoked_at = datetime.now(timezone.utc)
            self.db.commit()

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token"""
        try:
            payload = verify_token(refresh_token, "refresh")
            session_id = payload.get("session_id")
            user_id = payload.get("sub")

            if not session_id or not user_id:
                raise AuthenticationError("Invalid refresh token")

            # Check session
            session = self.db.query(UserSession).filter(
                and_(
                    UserSession.id == session_id,
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc)
                )
            ).first()

            if not session or not session.refresh_token_hash:
                raise AuthenticationError("Invalid or expired session")

            # Verify refresh token hash
            if not hash_api_key(refresh_token) == session.refresh_token_hash:
                raise AuthenticationError("Invalid refresh token")

            # Create new tokens
            token_data = {"sub": user_id, "session_id": session_id}
            access_token = create_access_token(token_data)
            new_refresh_token = create_refresh_token(token_data)

            # Update session
            session.refresh_token_hash = hash_api_key(new_refresh_token)
            session.last_active_at = datetime.now(timezone.utc)
            self.db.commit()

            return TokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=30 * 60  # 30 minutes
            )

        except Exception as e:
            raise AuthenticationError(f"Failed to refresh token: {str(e)}")

    async def get_current_user(self, token: str) -> Tuple[User, UserSession]:
        """Get current user from access token"""
        try:
            payload = verify_token(token, "access")
            user_id = payload.get("sub")
            session_id = payload.get("session_id")

            if not user_id or not session_id:
                raise AuthenticationError("Invalid token")

            # Get user and session
            user = self.db.query(User).filter(
                and_(User.id == user_id, User.deleted_at.is_(None))
            ).first()

            session = self.db.query(UserSession).filter(
                and_(
                    UserSession.id == session_id,
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc)
                )
            ).first()

            if not user or not session:
                raise AuthenticationError("Invalid or expired token")

            # Update last activity
            session.last_active_at = datetime.now(timezone.utc)
            self.db.commit()

            return user, session

        except Exception as e:
            raise AuthenticationError(f"Failed to get current user: {str(e)}")

    async def change_password(self, user_id: uuid.UUID, request: ChangePasswordRequest) -> None:
        """Change user password"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("User not found")

        # Verify old password
        if not verify_password(request.old_password, user.hashed_password):
            raise AuthenticationError("Invalid old password")

        # Update password
        user.hashed_password = hash_password(request.new_password)
        user.updated_at = datetime.now(timezone.utc)
        
        # Revoke all sessions except current one (optional)
        # self.db.query(UserSession).filter(UserSession.user_id == user_id).update({
        #     "is_active": False,
        #     "revoked_at": datetime.now(timezone.utc)
        # })
        
        self.db.commit()

    async def send_verification_email(self, email: str) -> None:
        """Send email verification"""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            # Don't reveal if email exists or not
            return

        # Generate verification token
        token = generate_verification_token(email, "email_verify")
        
        # Store verification record
        verification = UserVerification(
            user_id=user.id,
            verification_type="email_verify",
            token_hash=hash_api_key(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        self.db.add(verification)
        self.db.commit()

        # Send email
        await send_verification_email(email, token)

    async def verify_email(self, token: str) -> None:
        """Verify email address"""
        try:
            email = verify_verification_token(token, "email_verify")
            token_hash = hash_api_key(token)

            # Find verification record
            verification = self.db.query(UserVerification).filter(
                and_(
                    UserVerification.token_hash == token_hash,
                    UserVerification.verification_type == "email_verify",
                    UserVerification.expires_at > datetime.now(timezone.utc),
                    UserVerification.used_at.is_(None)
                )
            ).first()

            if not verification:
                raise AuthenticationError("Invalid or expired verification token")

            # Update user and verification
            user = self.db.query(User).filter(User.id == verification.user_id).first()
            if user:
                user.email_verified_at = datetime.now(timezone.utc)
                user.updated_at = datetime.now(timezone.utc)
            
            verification.used_at = datetime.now(timezone.utc)
            self.db.commit()

        except Exception as e:
            raise AuthenticationError(f"Email verification failed: {str(e)}")

    async def send_password_reset(self, email: str) -> None:
        """Send password reset email"""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            # Don't reveal if email exists or not
            return

        # Generate reset token
        token = generate_verification_token(email, "password_reset")
        
        # Store verification record
        verification = UserVerification(
            user_id=user.id,
            verification_type="password_reset",
            token_hash=hash_api_key(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        self.db.add(verification)
        self.db.commit()

        # Send email
        await send_password_reset_email(email, token)

    async def confirm_password_reset(self, token: str, new_password: str) -> None:
        """Confirm password reset and set new password"""
        try:
            email = verify_verification_token(token, "password_reset")
            token_hash = hash_api_key(token)

            # Find verification record
            verification = self.db.query(UserVerification).filter(
                and_(
                    UserVerification.token_hash == token_hash,
                    UserVerification.verification_type == "password_reset",
                    UserVerification.expires_at > datetime.now(timezone.utc),
                    UserVerification.used_at.is_(None)
                )
            ).first()

            if not verification:
                raise AuthenticationError("Invalid or expired reset token")

            # Update user password and verification
            user = self.db.query(User).filter(User.id == verification.user_id).first()
            if user:
                user.hashed_password = hash_password(new_password)
                user.updated_at = datetime.now(timezone.utc)
            
            verification.used_at = datetime.now(timezone.utc)
            
            # Revoke all user sessions
            self.db.query(UserSession).filter(UserSession.user_id == user.id).update({
                "is_active": False,
                "revoked_at": datetime.now(timezone.utc)
            })
            
            self.db.commit()

        except Exception as e:
            raise AuthenticationError(f"Password reset failed: {str(e)}")

    async def get_user_sessions(self, user_id: uuid.UUID) -> list[UserSessionResponse]:
        """Get all active sessions for a user"""
        sessions = self.db.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.now(timezone.utc)
            )
        ).order_by(UserSession.last_active_at.desc()).all()

        return [UserSessionResponse.from_orm(session) for session in sessions]

    async def revoke_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        """Revoke a specific user session"""
        session = self.db.query(UserSession).filter(
            and_(
                UserSession.id == session_id,
                UserSession.user_id == user_id
            )
        ).first()

        if session:
            session.is_active = False
            session.revoked_at = datetime.now(timezone.utc)
            self.db.commit()

    async def _create_user_session(
        self, 
        user_id: uuid.UUID, 
        device: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserSession:
        """Create a new user session"""
        session = UserSession(
            user_id=user_id,
            session_token_hash=hash_api_key(str(uuid.uuid4())),  # Temporary hash
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            ip_address=ip_address,
            user_agent=user_agent,
            last_active_at=datetime.now(timezone.utc)
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

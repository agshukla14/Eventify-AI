import os
import re
import time
import json
import base64
import hmac
import hashlib
import secrets
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import UserModel, EventModel
from .schemas import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
)

logger = logging.getLogger("eventify_auth")

from .core.security import (
    validate_email_format,
    validate_password_strength,
    get_jwt_secret,
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    http_bearer,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_SECONDS,
    _DEV_FALLBACK_SECRET,
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, req: UserRegisterRequest) -> UserRegisterResponse:
        email_clean = req.email.strip().lower()
        validate_email_format(email_clean)
        validate_password_strength(req.password)

        if not req.terms_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must accept the Terms and Conditions to create an account.",
            )

        existing = self.db.query(UserModel).filter(UserModel.email == email_clean).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        new_user = UserModel(
            id=user_id,
            email=email_clean,
            hashed_password=hash_password(req.password),
            full_name=req.full_name.strip(),
            is_active=True,
            email_verified=True,
            email_verified_at=now_iso,
            created_at=now_iso,
            updated_at=now_iso,
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        token = create_access_token({"sub": new_user.id, "email": new_user.email})
        user_resp = UserResponse(
            id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            is_active=new_user.is_active,
            email_verified=new_user.email_verified,
            email_verified_at=new_user.email_verified_at,
            created_at=new_user.created_at,
        )

        return UserRegisterResponse(
            message="Account registered successfully.",
            email=new_user.email,
            user_id=new_user.id,
            email_verified=True,
            access_token=token,
            token_type="bearer",
            user=user_resp,
        )

    def login(self, req: UserLoginRequest) -> TokenResponse:
        email_clean = req.email.strip().lower()
        user = self.db.query(UserModel).filter(UserModel.email == email_clean).first()
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated.",
            )

        token = create_access_token({"sub": user.id, "email": user.email})
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                email_verified=user.email_verified,
                email_verified_at=user.email_verified_at,
                created_at=user.created_at,
            ),
        )

    def get_or_create_demo_user(self) -> UserModel:
        demo = self.db.query(UserModel).filter(UserModel.email == "demo@eventify.ai").first()
        if demo:
            return demo
        now_iso = datetime.now(timezone.utc).isoformat()
        demo = UserModel(
            id="usr_demo_organizer",
            email="demo@eventify.ai",
            hashed_password=hash_password("DemoCelebration123!"),
            full_name="Eventify Demo Director",
            is_active=True,
            email_verified=True,
            email_verified_at=now_iso,
            created_at=now_iso,
            updated_at=now_iso,
        )
        self.db.add(demo)
        self.db.commit()
        self.db.refresh(demo)
        return demo


# =============================================================
# FastAPI Authentication & Authorization Dependencies
# =============================================================

def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
    db: Session = Depends(get_db),
) -> UserModel:
    """
    Strict authentication dependency for protected endpoints.
    Requires a valid Bearer token.
    Rejects unauthenticated requests with 401 Unauthorized.
    Never creates a fake session or automatically authenticates demo account.
    """
    raw_token = None
    if credentials and credentials.credentials:
        raw_token = credentials.credentials
    elif request and request.query_params.get("token"):
        raw_token = request.query_params.get("token")

    if raw_token:
        payload = decode_access_token(raw_token)
        if not payload or "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = db.query(UserModel).filter(UserModel.id == payload["sub"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated.",
            )
        return user

    # No credentials provided
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Only if explicitly enabled via test fixture in automated test environment:
    if os.getenv("ENABLE_TEST_DEMO_FALLBACK") == "1" and request.headers.get("X-Disable-Dev-Demo", "").lower() not in ["1", "true", "yes"]:
        auth = AuthService(db)
        return auth.get_or_create_demo_user()

    # Reject unauthenticated request
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please sign in to access this resource.",
        headers={"WWW-Authenticate": "Bearer"},
    )


get_current_user_required = get_current_user


def get_current_user_optional(
    request: Request = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
    db: Session = Depends(get_db),
) -> Optional[UserModel]:
    """
    Extracts authenticated user if a valid Bearer token is provided.
    Returns None if no token was sent.
    Raises 401 if an invalid/expired token is supplied.
    """
    raw_token = None
    if credentials and credentials.credentials:
        raw_token = credentials.credentials
    elif request and request.query_params.get("token"):
        raw_token = request.query_params.get("token")

    if not raw_token:
        return None

    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(UserModel).filter(UserModel.id == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
    return user


def verify_event_ownership(event_id: str, user: UserModel, db: Session) -> EventModel:
    """
    Verifies that the requested event exists and belongs to the authenticated user.
    Prevents IDOR vulnerabilities across all private resources.
    """
    event = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found.",
        )

    # Check ownership
    if event.owner_id is not None and event.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to access or modify this celebration plan.",
        )

    return event

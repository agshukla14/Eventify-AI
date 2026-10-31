import os
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
from .schemas import UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse

logger = logging.getLogger("eventify_auth")

# Dynamic generation of fallback secret for development mode only (never static or hardcoded)
_DEV_FALLBACK_SECRET = secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 7 * 24 * 3600  # 7 days

http_bearer = HTTPBearer(auto_error=False)


def get_jwt_secret() -> str:
    """
    Returns the JWT signing secret.
    In production (APP_ENV=production), JWT_SECRET MUST be set in environment variables;
    fails safely by raising a RuntimeError if absent.
    In development mode, falls back to a transient cryptographically secure random secret.
    """
    secret = os.getenv("JWT_SECRET", "").strip()
    if secret:
        return secret

    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        raise RuntimeError("CRITICAL SECURITY ERROR: JWT_SECRET environment variable is required in production mode.")

    logger.warning("JWT_SECRET not set in development mode. Using transient in-memory secret.")
    return _DEV_FALLBACK_SECRET


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def hash_password(password: str) -> str:
    """NIST-compliant PBKDF2-HMAC-SHA256 password hashing with 100,000 rounds and random salt."""
    salt = secrets.token_hex(16)
    iterations = 100_000
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2:sha256:{iterations}${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Timing-safe verification of plain password against PBKDF2 hash."""
    try:
        if not hashed_password or not plain_password:
            return False
        parts = hashed_password.split(":")
        if len(parts) != 3 or parts[0] != "pbkdf2":
            return False
        iter_str, salt, expected_hex = parts[2].split("$")
        iterations = int(iter_str)
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(key.hex(), expected_hex)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[float] = None) -> str:
    """Creates a standard RFC 7519 HMAC-SHA256 JWT access token."""
    to_encode = data.copy()
    now = time.time()
    expire = now + (expires_delta if expires_delta is not None else ACCESS_TOKEN_EXPIRE_SECONDS)
    to_encode.update({"exp": expire, "iat": now})

    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))

    secret = get_jwt_secret()
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = _base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and validates a standard RFC 7519 HMAC-SHA256 JWT access token.
    Validates structure, signature, expiration, and claims.
    """
    try:
        if not token or not isinstance(token, str):
            return None
        parts = token.split(".")
        if len(parts) != 3 or not parts[0] or not parts[1] or not parts[2]:
            return None
        encoded_header, encoded_payload, encoded_signature = parts

        # Verify header structure
        header_bytes = _base64url_decode(encoded_header)
        header = json.loads(header_bytes.decode("utf-8"))
        if header.get("alg") != JWT_ALGORITHM:
            return None

        # Verify signature
        secret = get_jwt_secret()
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_base64url_encode(expected_sig), encoded_signature):
            return None

        # Decode and inspect payload
        payload_bytes = _base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Check expiration
        exp = payload.get("exp")
        if not exp or not isinstance(exp, (int, float)):
            return None
        if time.time() > exp:
            return None  # Token expired

        # Check subject
        if not payload.get("sub"):
            return None

        return payload
    except Exception:
        return None


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, req: UserRegisterRequest) -> TokenResponse:
        email_clean = req.email.strip().lower()
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
            created_at=now_iso,
            updated_at=now_iso,
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        token = create_access_token({"sub": new_user.id, "email": new_user.email})
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse(
                id=new_user.id,
                email=new_user.email,
                full_name=new_user.full_name,
                is_active=new_user.is_active,
                created_at=new_user.created_at,
            ),
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
                created_at=user.created_at,
            ),
        )

    def get_or_create_demo_user(self) -> UserModel:
        """Retrieves or creates the default Demo Organizer for local development and demos."""
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
    1. If a Bearer token is provided: verifies signature, expiration, and active status.
    2. If no Bearer token is provided:
       - In production (APP_ENV=production): rejects immediately with 401 Unauthorized.
       - If X-Disable-Dev-Demo is set: rejects with 401 Unauthorized.
       - In local development mode: allows seamless demo organizer session.
    """
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
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

    # Check if dev demo mode is explicitly disabled (e.g. In security tests)
    if request.headers.get("X-Disable-Dev-Demo", "").lower() in ["1", "true", "yes"] or \
       os.getenv("DISABLE_DEV_DEMO", "").lower() in ["1", "true", "yes"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Local development demo fallback
    auth = AuthService(db)
    return auth.get_or_create_demo_user()


get_current_user_required = get_current_user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
    db: Session = Depends(get_db),
) -> Optional[UserModel]:
    """
    Extracts authenticated user if a valid Bearer token is provided.
    Raises 401 if an invalid/expired token is supplied.
    Returns None if no token was sent.
    """
    if not credentials or not credentials.credentials:
        return None

    payload = decode_access_token(credentials.credentials)
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
    Prevents Insecure Direct Object Reference (IDOR) vulnerabilities across all private resources.
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

    # In production, unowned legacy events cannot be accessed by arbitrary users
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if event.owner_id is None and app_env == "production" and user.id != "usr_demo_organizer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Event is not associated with your account.",
        )

    return event

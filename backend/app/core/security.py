import os
import re
import time
import json
import hmac
import hashlib
import base64
import secrets
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer

logger = logging.getLogger("eventify_security")

_DEV_FALLBACK_SECRET = "eventify-dev-transient-secret-key-32chars-min-ok"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 7 * 24 * 3600  # 7 days

http_bearer = HTTPBearer(auto_error=False)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email_format(email: str) -> None:
    if not email or not EMAIL_REGEX.match(email.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address format.",
        )


def validate_password_strength(password: str) -> None:
    if not password or len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long.",
        )
    has_letter = any(c.isalpha() for c in password)
    has_digit_or_symbol = any(c.isdigit() or not c.isalnum() for c in password)
    if not (has_letter and has_digit_or_symbol):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain both letters and at least one number or special character.",
        )


def get_jwt_secret() -> str:
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

        header_bytes = _base64url_decode(encoded_header)
        header = json.loads(header_bytes.decode("utf-8"))
        if header.get("alg") != JWT_ALGORITHM:
            return None

        secret = get_jwt_secret()
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_base64url_encode(expected_sig), encoded_signature):
            return None

        payload_bytes = _base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))

        exp = payload.get("exp")
        if not exp or not isinstance(exp, (int, float)):
            return None
        if time.time() > exp:
            return None

        if not payload.get("sub"):
            return None

        return payload
    except Exception:
        return None


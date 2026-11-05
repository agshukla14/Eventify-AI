"""
Configuration module for Eventify AI.
Loads settings from environment and core configuration.
"""
from .core.config import (
    BASE_DIR,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    APP_ENV,
    PORT,
    FRONTEND_PORT,
    DATABASE_URL,
    DEFAULT_CURRENCY,
    JWT_SECRET,
    ALLOWED_ORIGINS,
)

__all__ = [
    "BASE_DIR",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "APP_ENV",
    "PORT",
    "FRONTEND_PORT",
    "DATABASE_URL",
    "DEFAULT_CURRENCY",
    "JWT_SECRET",
    "ALLOWED_ORIGINS",
]

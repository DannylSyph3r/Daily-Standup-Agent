"""
Configuration package for Daily Standup Agent
Exports all settings and validation functions
"""

from .settings import (
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    DATABASE_URL,
    APP_NAME,
    TIMEZONE,
    WINDOW_START,
    WINDOW_END,
    A2A_PORT,
    validate_config
)

from .environment import check_environment

__all__ = [
    'GOOGLE_API_KEY',
    'GEMINI_MODEL',
    'DATABASE_URL',
    'APP_NAME',
    'TIMEZONE',
    'WINDOW_START',
    'WINDOW_END',
    'A2A_PORT',
    'validate_config',
    'check_environment'
]
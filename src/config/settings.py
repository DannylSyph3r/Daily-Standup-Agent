"""
Configuration settings for Daily Standup Agent
All environment-based configuration in one place
"""
import os
from datetime import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
DATABASE_URL = os.getenv("DATABASE_URL")
APP_NAME = os.getenv("APP_NAME", "daily_standup_agent")
TIMEZONE = os.getenv("TIMEZONE", "Africa/Lagos")
WINDOW_START_HOUR = int(os.getenv("WINDOW_START_HOUR", "9"))
WINDOW_START_MINUTE = int(os.getenv("WINDOW_START_MINUTE", "30"))
WINDOW_END_HOUR = int(os.getenv("WINDOW_END_HOUR", "12"))
WINDOW_END_MINUTE = int(os.getenv("WINDOW_END_MINUTE", "30"))
WINDOW_START = time(WINDOW_START_HOUR, WINDOW_START_MINUTE)
WINDOW_END = time(WINDOW_END_HOUR, WINDOW_END_MINUTE)
A2A_PORT = int(os.getenv("A2A_PORT", "8001"))


def validate_config():
    """Validate that all required configuration is present."""
    errors = []
    
    if not GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY is required")
    
    if not DATABASE_URL:
        errors.append("DATABASE_URL is required")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True
"""
Environment validation for Daily Standup Agent
Checks all required dependencies and configurations
"""
import sys
from src.config.settings import validate_config


def check_environment() -> bool:
    """
    Check if the environment is properly configured for the standup agent.
    
    Returns:
        bool: True if environment is properly configured, False otherwise
    """
    print("\n" + "=" * 60)
    print("Daily Standup Agent - Environment Check")
    print("=" * 60)
    
    # Test ADK imports
    try:
        from google.adk.agents import LlmAgent
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
        print("✓ Google ADK imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ADK modules: {e}")
        print("  Solution: pip install google-adk")
        return False
    
    # Test asyncpg import
    try:
        import asyncpg
        print("✓ asyncpg imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import asyncpg: {e}")
        print("  Solution: pip install asyncpg")
        return False
    
    # Test pytz import
    try:
        import pytz
        print("✓ pytz imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import pytz: {e}")
        print("  Solution: pip install pytz")
        return False
    
    # Validate configuration
    try:
        validate_config()
        print("✓ Configuration validated successfully")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        print("  Solution: Check your .env file")
        return False
    
    print("=" * 60)
    print("✓ Environment check passed!")
    print("=" * 60)
    print()
    
    return True


if __name__ == "__main__":
    if not check_environment():
        print("\n⚠️  Environment check failed!")
        print("Please fix the issues above before running the agent.")
        sys.exit(1)
    else:
        print("\n✓ Environment is ready!")
        print("You can now run: python main.py")
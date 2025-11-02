"""
Daily Standup Agent - Main Entry Point
Exposes the agent via A2A protocol for platform-agnostic integration
"""
import asyncio
import sys
from src.config import check_environment, A2A_PORT, APP_NAME
from src.agents import standup_agent
from src.database import create_pool, close_pool


async def initialize_agent():
    """Initialize the agent and database connection."""
    print("\n" + "=" * 70)
    print("Daily Standup Agent - Initialization")
    print("=" * 70)
    
    # Check environment
    if not check_environment():
        print("\n⚠️  Environment check failed!")
        print("Please fix the configuration issues before starting the agent.")
        sys.exit(1)
    
    # Create database pool
    try:
        await create_pool()
        print("✓ Database connection established")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("\nPlease ensure:")
        print("1. PostgreSQL is running")
        print("2. DATABASE_URL in .env is correct")
        print("3. Database schema is created (run database/schema.sql)")
        sys.exit(1)
    
    print("=" * 70)
    print("✓ Agent initialized successfully!")
    print("=" * 70)
    print()


async def shutdown_agent():
    """Cleanup on shutdown."""
    print("\n" + "=" * 70)
    print("Shutting down Daily Standup Agent...")
    print("=" * 70)
    
    await close_pool()
    
    print("=" * 70)
    print("✓ Agent shut down successfully")
    print("=" * 70)


def start_a2a_server():
    """
    Start the A2A server to expose the agent.
    
    This makes the agent accessible via the A2A protocol at:
    http://localhost:{A2A_PORT}/a2a/agent/dailyStandupAgent
    """
    from google.adk.a2a import to_a2a
    import uvicorn
    
    print("\n" + "=" * 70)
    print("Starting A2A Server")
    print("=" * 70)
    print(f"Agent Name: {standup_agent.name}")
    print(f"Port: {A2A_PORT}")
    print(f"A2A Endpoint: http://localhost:{A2A_PORT}/")
    print("=" * 70)
    print()
    print("The agent is now accessible via A2A protocol!")
    print("A2A platforms can connect to this agent using the endpoint above.")
    print()
    print("Press CTRL+C to stop the server")
    print("=" * 70)
    print()
    
    # Initialize agent before starting server
    asyncio.run(initialize_agent())
    
    # Convert agent to A2A and start server
    try:
        app = to_a2a(standup_agent)
        
        # Run with uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=A2A_PORT,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nReceived shutdown signal...")
    finally:
        asyncio.run(shutdown_agent())


def main():
    """Main entry point."""
    try:
        start_a2a_server()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Handle nested event loop for certain environments
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        print("Note: nest_asyncio not available - running without nested loop support")
    
    main()
"""
Daily Standup Agent - Main Entry Point
Runs the agent with ADK's built-in server
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


def start_server():
    """
    Start the ADK development server.
    
    The agent will be accessible at:
    http://localhost:8001
    """
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    print("\n" + "=" * 70)
    print("Starting Daily Standup Agent Server")
    print("=" * 70)
    print(f"Agent Name: {standup_agent.name}")
    print(f"Port: {A2A_PORT}")
    print("=" * 70)
    print()
    
    # Initialize agent
    asyncio.run(initialize_agent())
    
    # Create FastAPI app
    app = FastAPI(title="Daily Standup Agent")
    
    # Create session service and runner
    session_service = InMemorySessionService()
    runner = Runner(
        agent=standup_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    @app.get("/")
    async def root():
        return JSONResponse({
            "name": "Daily Standup Agent",
            "status": "running",
            "description": "AI-powered daily standup coordinator",
            "endpoints": {
                "health": "/health",
                "agent_info": "/info",
                "chat": "/chat"
            }
        })
    
    @app.get("/health")
    async def health():
        return JSONResponse({"status": "healthy"})
    
    @app.get("/info")
    async def info():
        return JSONResponse({
            "agent_name": standup_agent.name,
            "model": standup_agent.model,
            "description": standup_agent.description,
            "capabilities": [
                "Standup collection (9:30 AM - 12:30 PM WAT)",
                "Team summary generation",
                "Historical query support"
            ]
        })
    
    @app.post("/chat")
    async def chat(request: dict):
        """
        Chat endpoint for interacting with the agent.
        
        Request body:
        {
            "message": "Your message here",
            "session_id": "optional-session-id",
            "user_id": "optional-user-id"
        }
        """
        try:
            from google.genai.types import Content, Part
            
            message = request.get("message", "")
            session_id = request.get("session_id", "default")
            user_id = request.get("user_id", "default_user")
            
            if not message:
                return JSONResponse(
                    {"error": "Message is required"},
                    status_code=400
                )
            
            # Create content
            user_content = Content(parts=[Part(text=message)])
            
            # Run agent
            response_text = ""
            async for event in runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=user_content
            ):
                if event.is_final_response():
                    response_text = event.content.parts[0].text if event.content else ""
            
            return JSONResponse({
                "response": response_text,
                "session_id": session_id
            })
            
        except Exception as e:
            print(f"Error in chat endpoint: {e}")
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )
    
    print("Agent is now running!")
    print(f"Access the agent at: http://localhost:{A2A_PORT}")
    print(f"API endpoints:")
    print(f"  - GET  /       : Root info")
    print(f"  - GET  /health : Health check")
    print(f"  - GET  /info   : Agent info")
    print(f"  - POST /chat   : Chat with agent")
    print()
    print("Press CTRL+C to stop the server")
    print("=" * 70)
    print()
    
    try:
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
        start_server()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
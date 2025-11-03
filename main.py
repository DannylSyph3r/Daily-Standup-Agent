"""
Daily Standup Agent - Main Entry Point
Runs the agent with ADK's built-in server
"""
import asyncio
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.config import check_environment, A2A_PORT, APP_NAME, DATABASE_URL
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


def build_telex_response(
    request_id: str,
    context_id: str,
    response_text: str,
    message_id: str,
    task_id: str,
    history: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build a Telex-formatted JSON-RPC 2.0 response.
    
    Args:
        request_id: Original request ID
        context_id: Context ID for session tracking
        response_text: Agent's response text
        message_id: Unique message ID
        task_id: Task ID
        history: Conversation history
        
    Returns:
        Telex-formatted response dictionary
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Build response message
    response_message = {
        "kind": "message",
        "role": "agent",
        "parts": [
            {
                "kind": "text",
                "text": response_text,
                "data": None,
                "file_url": None
            }
        ],
        "messageId": message_id,
        "taskId": task_id,
        "metadata": None
    }
    
    # Build artifacts (including the response)
    artifacts = [
        {
            "artifactId": str(uuid.uuid4()),
            "name": "standup_agent_response",
            "parts": [
                {
                    "kind": "text",
                    "text": response_text,
                    "data": None,
                    "file_url": None
                }
            ]
        }
    ]
    
    # Add response to history
    if history is None:
        history = []
    history.append(response_message)
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "id": task_id,
            "contextId": context_id,
            "status": {
                "state": "completed",
                "timestamp": timestamp,
                "message": response_message
            },
            "artifacts": artifacts,
            "history": history,
            "kind": "task"
        },
        "error": None
    }


def start_server():
    """
    Start the ADK development server.
    
    The agent will be accessible at:
    http://localhost:8001
    """
    from google.adk.runners import Runner
    from google.adk.sessions import DatabaseSessionService
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from google.genai.types import Content, Part
    
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
    print(f"🔗 Initializing DatabaseSessionService with: {DATABASE_URL}")
    session_service = DatabaseSessionService(db_url=DATABASE_URL)
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
                "chat": "/chat (simple testing)",
                "telex": "/telex (Telex A2A integration)"
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
        Simple chat endpoint for testing with Postman.
        
        Request body:
        {
            "message": "Your message here",
            "session_id": "optional-session-id"  // If not provided, generates UUID
        }
        
        Response:
        {
            "response": "Agent's response text",
            "session_id": "session-id-used"
        }
        """
        try:
            message = request.get("message", "")
            
            # Get or generate session_id for testing
            session_id = request.get("session_id")
            if not session_id:
                session_id = f"chat-{str(uuid.uuid4())}"
            
            user_id = session_id  # Use same value for simplicity
            
            if not message:
                return JSONResponse(
                    {"error": "Message is required"},
                    status_code=400
                )
            
            # Get or create session (get_session returns None if not found)
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id
            )
            
            if session is None:
                # Create new session if doesn't exist
                session = await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                    state={}
                )
                print(f"✨ Created new session: {session_id}")
            else:
                print(f"📝 Retrieved existing session: {session_id}")
            
            # Create content
            user_content = Content(parts=[Part(text=message)])
            
            # Run agent
            response_text = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=user_content
            ):
                if event.is_final_response():
                    response_text = event.content.parts[0].text if event.content else ""
            
            return JSONResponse({
                "response": response_text,
                "session_id": session.id
            })
            
        except Exception as e:
            print(f"Error in chat endpoint: {e}")
            import traceback
            traceback.print_exc()
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )
    
    @app.post("/telex")
    async def telex(request: Request):
        """
        Telex A2A webhook endpoint.
        
        Accepts JSON-RPC 2.0 format:
        {
            "jsonrpc": "2.0",
            "id": "request-id",
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "role": "user",
                    "parts": [{"kind": "text", "text": "..."}],
                    "messageId": "msg-id"
                },
                "contextId": "context-id",  // Session identifier
                "configuration": {...}
            }
        }
        
        Returns Telex-formatted JSON-RPC 2.0 response with artifacts and history.
        """
        try:
            # Parse request body
            body = await request.json()
            
            print("\n" + "=" * 70)
            print("Incoming Telex Request")
            print("=" * 70)
            
            # Extract JSON-RPC fields
            request_id = body.get("id", str(uuid.uuid4()))
            method = body.get("method", "")
            params = body.get("params", {})
            
            print(f"Request ID: {request_id}")
            print(f"Method: {method}")
            
            # Extract contextId (session identifier from Telex)
            context_id = params.get("contextId")
            if not context_id:
                context_id = str(uuid.uuid4())
                print(f"⚠️  No contextId provided, generated: {context_id}")
            else:
                print(f"Context ID: {context_id}")
            
            # Extract message
            message_data = params.get("message", {})
            parts = message_data.get("parts", [])
            
            # Extract text from parts (handle multiple parts)
            message_text = ""
            for part in parts:
                if part.get("kind") == "text":
                    message_text += part.get("text", "") + " "
            
            message_text = message_text.strip()
            
            if not message_text:
                print("⚠️  No message text found in request")
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "No message text found in request"
                    }
                })
            
            print(f"Message: {message_text}")
            print("=" * 70)
            
            # Use contextId as both session_id and user_id
            session_id = context_id
            user_id = context_id
            
            # Get or create session (get_session returns None if not found)
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id
            )
            
            if session is None:
                # Create new session if doesn't exist
                session = await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                    state={}
                )
                print(f"✨ Created new session: {session_id}")
            else:
                print(f"📝 Retrieved existing session: {session_id}")
            
            # Create content
            user_content = Content(parts=[Part(text=message_text)])
            
            # Run agent
            response_text = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=user_content
            ):
                if event.is_final_response():
                    response_text = event.content.parts[0].text if event.content else ""
            
            print(f"\nResponse: {response_text[:100]}...")
            print("=" * 70)
            
            # Generate IDs for response
            task_id = str(uuid.uuid4())
            message_id = str(uuid.uuid4())
            
            # Build history (include user message and agent response)
            history = [
                {
                    "kind": "message",
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": message_text,
                            "data": None,
                            "file_url": None
                        }
                    ],
                    "messageId": message_data.get("messageId", str(uuid.uuid4())),
                    "taskId": None,
                    "metadata": None
                }
            ]
            
            # Build Telex-formatted response
            telex_response = build_telex_response(
                request_id=request_id,
                context_id=context_id,
                response_text=response_text,
                message_id=message_id,
                task_id=task_id,
                history=history
            )
            
            return JSONResponse(telex_response)
            
        except Exception as e:
            print(f"\n❌ Error in Telex endpoint: {e}")
            import traceback
            traceback.print_exc()
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id", "unknown") if 'body' in locals() else "unknown",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            })
    
    print("Agent is now running!")
    print(f"Access the agent at: http://localhost:{A2A_PORT}")
    print(f"\nEndpoints:")
    print(f"  GET  /         - Root info")
    print(f"  GET  /health   - Health check")
    print(f"  GET  /info     - Agent info")
    print(f"  POST /chat     - Simple chat (for Postman testing)")
    print(f"  POST /telex    - Telex A2A webhook (for production)")
    print(f"\nSession Management:")
    print(f"  /chat  - Uses 'session_id' from request or generates UUID")
    print(f"  /telex - Uses Telex's 'contextId' as session_id")
    print(f"  Sessions stored in PostgreSQL (survives restarts!)")
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
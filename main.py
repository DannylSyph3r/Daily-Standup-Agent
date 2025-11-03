"""
Daily Standup Agent - Main Entry Point (FIXED)
Runs the agent with ADK's built-in server with proper async handling
"""
import asyncio
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.config import check_environment, A2A_PORT, APP_NAME, DATABASE_URL
from src.agents import standup_agent
from src.database import create_pool, close_pool


@asynccontextmanager
async def lifespan(app):
    """
    FastAPI lifespan event handler.
    Properly initializes and cleans up resources within FastAPI's event loop.
    """
    # ===== STARTUP =====
    print("\n" + "=" * 70)
    print("Daily Standup Agent - Initialization")
    print("=" * 70)
    
    # Check environment
    if not check_environment():
        print("\n⚠️  Environment check failed!")
        print("Please fix the configuration issues before starting the agent.")
        sys.exit(1)
    
    # Create database pool IN THE FASTAPI EVENT LOOP
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
    
    # Yield control to the application
    yield
    
    # ===== SHUTDOWN =====
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
        request_id: The request ID from the incoming request
        context_id: The context ID (conversation ID)
        response_text: The agent's response text
        message_id: Generated message ID for this response
        task_id: Task ID for tracking
        history: Conversation history
        
    Returns:
        Telex-formatted JSON-RPC 2.0 response dict
    """
    if history is None:
        history = []
    
    # Build assistant response message
    assistant_message = {
        "kind": "message",
        "role": "assistant",
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
    
    # Append to history
    history.append(assistant_message)
    
    # Build Telex response
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "task_id": task_id,
            "context_id": context_id,
            "history": history
        }
    }


def start_server():
    """
    Start the FastAPI server with proper async initialization.
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
    
    # Create FastAPI app WITH LIFESPAN
    app = FastAPI(
        title="Daily Standup Agent",
        lifespan=lifespan  # This is the key fix!
    )
    
    # Create session service and runner (NOT async operations)
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
        
        Expected Telex JSON-RPC 2.0 request format:
        {
            "jsonrpc": "2.0",
            "method": "agent/sendMessage",
            "params": {
                "contextId": "conversation-uuid",
                "message": {
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": "User's message"
                    }]
                },
                "history": [...previous messages...]
            },
            "id": "request-uuid"
        }
        
        Returns Telex-formatted JSON-RPC 2.0 response
        """
        try:
            body = await request.json()
            
            # Extract request components
            request_id = body.get("id", str(uuid.uuid4()))
            method = body.get("method")
            params = body.get("params", {})
            
            print("\n" + "=" * 70)
            print(f"📬 Incoming Telex Request")
            print(f"Method: {method}")
            print(f"Request ID: {request_id}")
            print("=" * 70)
            
            if method != "agent/sendMessage":
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found"
                    }
                })
            
            # Extract message data
            context_id = params.get("contextId")
            message_data = params.get("message", {})
            
            # Extract text from message content
            content = message_data.get("content", [])
            message_text = ""
            for content_item in content:
                if content_item.get("type") == "text":
                    message_text = content_item.get("text", "")
                    break
            
            if not context_id or not message_text:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: contextId and message.content required"
                    }
                })
            
            print(f"Context ID: {context_id}")
            print(f"Message: {message_text}")
            print("=" * 70)
            
            # Use contextId as both session_id and user_id
            session_id = context_id
            user_id = context_id
            
            # Get or create session
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id
            )
            
            if session is None:
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
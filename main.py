"""
Daily Standup Agent - Main Entry Point
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
    # STARTUP
    print("\n" + "=" * 70)
    print("Daily Standup Agent - Initialization")
    print("=" * 70)
    
    # Check environment
    if not check_environment():
        print("\n Environment check failed!")
        print("Please fix the configuration issues before starting the agent.")
        sys.exit(1)
    
    # Create database pool in the FastAPI Event Loop
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
    
    yield
    
    # SHUTDOWN
    print("\n" + "=" * 70)
    print("Shutting down Daily Standup Agent...")
    print("=" * 70)
    
    await close_pool()
    
    print("=" * 70)
    print("✓ Agent shut down successfully")
    print("=" * 70)


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
    from src.utils.a2a_serializer import (
        parse_telex_request,
        build_a2a_response,
        build_a2a_error_response
    )
    
    print("\n" + "=" * 70)
    print("Starting Daily Standup Agent Server")
    print("=" * 70)
    print(f"Agent Name: {standup_agent.name}")
    print(f"Port: {A2A_PORT}")
    print("=" * 70)
    print()
    
    app = FastAPI(
        title="Daily Standup Agent",
        lifespan=lifespan
    )
    
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
                "agent_card": "/.well-known/agent.json",
                "health": "/health",
                "agent_info": "/info",
                "chat": "/ (POST)"
            }
        })

    @app.get("/.well-known/agent.json")
    async def get_agent_card():
        """
        Return the agent card for Telex integration.
        """
        return JSONResponse({
            "name": standup_agent.name,
            "description": standup_agent.description,
            "url": "/",
            "healthCheck": "/health",
            "capabilities": [
                {
                    "name": "Standup Collection",
                    "description": "Collects daily standup updates during a specific time window."
                },
                {
                    "name": "Team Summary",
                    "description": "Generates AI-powered team summaries on demand."
                }
            ],
            "metadata": {
                "model": standup_agent.model,
                "timezone": "Africa/Lagos",
                "submission_window": "9:30 AM - 12:30 PM WAT"
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
                "Historical query support",
                "Daily session management per user"
            ]
        })
    
    @app.post("/")
    async def handle_rpc(request: Request):
        """
        Unified JSON-RPC endpoint supporting Telex A2A format
        and simple format for testing.
        
        This is the main communication endpoint.
        
        SIMPLE FORMAT (for Postman testing):
        {
            "message": "Your message here",
            "session_id": "optional-session-id"
        }
        
        TELEX A2A FORMAT (JSON-RPC):
        {
            "jsonrpc": "2.0",
            "id": "request-uuid",
            "method": "message/send", // This routes the request
            "params": {
                "message": {
                    "kind": "message",
                    "role": "user",
                    "parts": [{"kind": "text", "text": "..."}],
                    "metadata": { ... }
                }
            }
        }
        
        SESSION MANAGEMENT (Telex):
        Each user gets a daily session: {telex_user_id}-{DDMMYYYY}
        """
        try:
            body = await request.json()
            
            # Detect request format
            is_telex_format = "jsonrpc" in body and "method" in body
            
            if is_telex_format:
                
                print("\n" + "=" * 70)
                print("📬 Incoming Telex A2A Request (JSON-RPC)")
                print("=" * 70)
                
                # Parse Telex request with flexible field extraction
                parsed = parse_telex_request(body)
                
                request_id = parsed["request_id"]
                method = parsed["method"]
                message_text = parsed["message_text"]
                context_id = parsed["context_id"]
                session_id = parsed["session_id"]
                telex_user_id = parsed["telex_user_id"]
                user_message_id = parsed["message_id"]
                
                print(f"Method: {method}")
                print(f"Request ID: {request_id}")
                print(f"Context ID: {context_id}")
                print(f"Session ID: {session_id}")
                print(f"Telex User ID: {telex_user_id}")
                print(f"Message: {message_text}")
                print("=" * 70)
                
                # ROUTING BASED ON METHOD     
                if method and ("message" in method.lower() or "send" in method.lower()):
                    # This is a message to be processed by the agent
                    
                    # Validate message
                    if not message_text:
                        return JSONResponse(
                            build_a2a_error_response(
                                request_id=request_id,
                                error_code=-32602,
                                error_message="Invalid params: message text is required"
                            )
                        )
                    
                    # Use session_id (daily session per user)
                    user_id = session_id
                    
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
                        print(f"✨ Created new daily session: {session_id}")
                    else:
                        print(f"📝 Retrieved existing daily session: {session_id}")
                    
                    # Create content
                    user_content = Content(parts=[Part(text=message_text)])
                    
                    response_text = ""
                    
                    async for event in runner.run_async(
                        user_id=user_id,
                        session_id=session.id,
                        new_message=user_content
                    ):
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    response_text = part.text.strip()
                                
                                if hasattr(part, 'function_response') and part.function_response:
                                    if (part.function_response.response and 
                                        'result' in part.function_response.response and 
                                        part.function_response.response['result']):
                                        
                                        response_text = part.function_response.response['result'].strip()
                    
                    print(f"\n✅ Response: {response_text[:100] if response_text else '(empty)'}...")
                    print("=" * 70)
                    
                    # Build A2A-compliant response
                    a2a_response = build_a2a_response(
                        request_id=request_id,
                        context_id=context_id,
                        response_text=response_text,
                        user_message_text=message_text,
                        user_message_id=user_message_id
                    )
                    
                    return JSONResponse(a2a_response)
                
                else:
                    # Method not supported
                    return JSONResponse(
                        build_a2a_error_response(
                            request_id=request_id,
                            error_code=-32601,
                            error_message=f"Method '{method}' not supported"
                        )
                    )
                
            else:
                
                print("\n" + "=" * 70)
                print("📬 Incoming Simple Chat Request (Non-JSON-RPC)")
                print("=" * 70)
                
                message = body.get("message", "")
                
                # Get or generate session_id
                session_id = body.get("session_id")
                if not session_id:
                    session_id = f"chat-{str(uuid.uuid4())}"
                
                user_id = session_id
                
                if not message:
                    return JSONResponse(
                        {"error": "Message is required"},
                        status_code=400
                    )
                
                print(f"Session ID: {session_id}")
                print(f"Message: {message}")
                print("=" * 70)
                
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
                user_content = Content(parts=[Part(text=message)])

                response_text = ""
                
                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session.id,
                    new_message=user_content
                ):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text = part.text.strip()
                            
                            if hasattr(part, 'function_response') and part.function_response:
                                if (part.function_response.response and 
                                    'result' in part.function_response.response and 
                                    part.function_response.response['result']):
                                    
                                    response_text = part.function_response.response['result'].strip()
                
                print(f"\n✅ Response: {response_text[:100] if response_text else '(empty)'}...")
                print("=" * 70)
                
                return JSONResponse({
                    "response": response_text,
                    "session_id": session.id
                })
            
        except Exception as e:
            print(f"\n❌ Error in chat endpoint: {e}")
            import traceback
            traceback.print_exc()
            
            # Determine if we should return A2A error or simple error
            if 'body' in locals() and isinstance(body, dict) and "jsonrpc" in body:
                return JSONResponse(
                    build_a2a_error_response(
                        request_id=body.get("id", "unknown"),
                        error_code=-32603,
                        error_message=f"Internal error: {str(e)}"
                    ),
                    status_code=500
                )
            else:
                return JSONResponse(
                    {"error": str(e)},
                    status_code=500
                )

    print("Agent is now running!")
    print(f"Access the agent at: http://localhost:{A2A_PORT}")
    print(f"\nEndpoints:")
    print(f"  GET  /         - Root info")
    print(f"  GET  /health   - Health check")
    print(f"  GET  /info     - Agent info")
    print(f"  GET  /.well-known/agent.json - Telex Agent Card")
    print(f"  POST /         - Unified endpoint (JSON-RPC + Simple)")
    print(f"\nSupported Formats:")
    print(f"  Simple:  {{'message': '...', 'session_id': '...'}}")
    print(f"  Telex:   {{'jsonrpc': '2.0', 'method': 'message/send', 'params': {{...}}}}")
    print(f"\nSession Management:")
    print(f"  Simple format - Uses 'session_id' from request or generates UUID")
    print(f"  Telex format  - Daily sessions per user: {{user_id}}-{{DDMMYYYY}}")
    print(f"                  Example: 019a4af5-87c9-7309-a8fb-9df58d1b917a-04112025")
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
"""
A2A (Agent-to-Agent) Protocol Serializer
Handles Telex JSON-RPC 2.0 request/response formatting with flexible parsing
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional


def generate_daily_session_id(telex_user_id: str) -> str:
    """
    Generate a daily session ID using telex_user_id + current date.
    
    Format: {telex_user_id}-{DDMMYYYY}
    Example: 019a4af5-87c9-7309-a8fb-9df58d1b917a-04112025
    
    This ensures each user has their own session per day, allowing the agent
    to maintain context for that user throughout the day.
    
    Args:
        telex_user_id: User ID from Telex metadata
        
    Returns:
        Daily session ID string
    """
    today = datetime.utcnow().strftime("%d%m%Y")
    return f"{telex_user_id}-{today}"


def extract_text_from_telex_message(message: Dict[str, Any]) -> str:
    """
    Extract text from Telex message structure with multiple fallback strategies.
    
    Telex can send messages in various formats. This function tries multiple
    locations to find the actual user text:
    1. Direct text in first part
    2. Content field with text
    3. Data arrays with conversation history
    4. Any text field anywhere in the structure
    
    Args:
        message: Telex message object (can vary in structure)
        
    Returns:
        Extracted text string (empty string if not found)
    """
    if not message:
        return ""
    
    # Strategy 1: Check for direct 'text' field at message level
    if "text" in message and isinstance(message["text"], str):
        text = message["text"].strip()
        if text:
            return text
    
    # Strategy 2: Check parts array
    parts = message.get("parts", [])
    if parts and isinstance(parts, list):
        for part in parts:
            if not isinstance(part, dict):
                continue
            
            # Check for direct text in part
            if part.get("kind") == "text" and "text" in part:
                text = part.get("text", "").strip()
                # Filter out HTML tags if present
                if text and not text.startswith("<"):
                    return text
            
            # Check for text in nested data
            if part.get("kind") == "data" and "data" in part:
                data_array = part.get("data", [])
                if isinstance(data_array, list):
                    # Get the last text item (most recent user message)
                    for data_item in reversed(data_array):
                        if isinstance(data_item, dict) and data_item.get("kind") == "text":
                            text = data_item.get("text", "").strip()
                            # Prefer non-HTML text
                            if text and not text.startswith("<"):
                                return text
    
    # Strategy 3: Check content array (alternative structure)
    content = message.get("content", [])
    if content and isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    text = item.get("text", "").strip()
                    if text:
                        return text
    
    # Strategy 4: Deep search for any 'text' field
    def find_text_recursive(obj):
        if isinstance(obj, dict):
            if "text" in obj and isinstance(obj["text"], str):
                text = obj["text"].strip()
                if text and not text.startswith("<"):
                    return text
            for value in obj.values():
                result = find_text_recursive(value)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = find_text_recursive(item)
                if result:
                    return result
        return None
    
    found_text = find_text_recursive(message)
    if found_text:
        return found_text
    
    return ""


def extract_context_id(body: Dict[str, Any]) -> str:
    """
    Extract context/session ID from various possible locations.
    
    Args:
        body: Request body
        
    Returns:
        Context ID (generates UUID if not found)
    """
    # Try params.contextId
    params = body.get("params", {})
    if "contextId" in params:
        return str(params["contextId"])
    
    # Try params.context_id
    if "context_id" in params:
        return str(params["context_id"])
    
    # Try metadata
    message = params.get("message", {})
    metadata = message.get("metadata", {})
    
    # Try telex_channel_id
    if "telex_channel_id" in metadata:
        return str(metadata["telex_channel_id"])
    
    # Try channel_id
    if "channel_id" in metadata:
        return str(metadata["channel_id"])
    
    # Try conversation_id
    if "conversation_id" in metadata:
        return str(metadata["conversation_id"])
    
    # Try sessionId
    if "sessionId" in params:
        return str(params["sessionId"])
    
    # Generate fallback
    return f"telex-{str(uuid.uuid4())}"


def parse_telex_request(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse incoming Telex A2A request with flexible field detection.
    
    Args:
        body: Raw request body from Telex
        
    Returns:
        Parsed request with extracted fields (uses defaults if fields missing)
    """
    request_id = body.get("id", str(uuid.uuid4()))
    method = body.get("method", "message/send")
    params = body.get("params", {})
    
    message_obj = params.get("message", {})
    message_id = message_obj.get("messageId") or message_obj.get("message_id") or str(uuid.uuid4())
    metadata = message_obj.get("metadata", {})
    
    # Extract text with flexible parsing
    text = extract_text_from_telex_message(message_obj)
    
    # Extract context ID from multiple possible locations
    context_id = extract_context_id(body)
    
    # Extract user ID with fallbacks
    telex_user_id = (
        metadata.get("telex_user_id") or 
        metadata.get("user_id") or 
        metadata.get("userId") or
        ""
    )
    
    # Generate session ID with multiple fallback strategies
    if telex_user_id:
        # Best case: Generate daily session ID using telex_user_id
        try:
            session_id = generate_daily_session_id(telex_user_id)
        except Exception as e:
            print(f"Warning: Failed to generate daily session ID: {e}")
            # Fallback to context_id or generated UUID
            session_id = context_id if context_id else f"session-{str(uuid.uuid4())}"
    else:
        # No telex_user_id: use context_id if available, otherwise generate new UUID
        session_id = context_id if context_id else f"session-{str(uuid.uuid4())}"
        print(f"Warning: No telex_user_id found, using fallback session ID: {session_id}")
    
    return {
        "request_id": request_id,
        "method": method,
        "message_text": text,
        "message_id": message_id,
        "context_id": context_id,
        "session_id": session_id,  # Daily session ID for user (with fallbacks)
        "telex_user_id": telex_user_id,
        "metadata": metadata,
        "configuration": params.get("configuration", {})
    }


def build_a2a_response(
    request_id: str,
    context_id: str,
    response_text: str,
    user_message_text: str = "",
    user_message_id: Optional[str] = None,
    task_id: Optional[str] = None,
    agent_message_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build A2A-compliant JSON-RPC 2.0 response (FIXED: Simple Message structure).
    
    This function generates the simplified "Message" structure
    expected by the Telex endpoint, placing it directly in the 'result' field.
    
    This corrected version now includes the 'contextId' in the top-level
    Message object, as it is passed by main.py and likely required
    by the receiving system for context.
    
    Args:
        request_id: Original request ID from Telex
        context_id: Context/session identifier
        response_text: Agent's response text
        user_message_text: Original user message (retained, not used)
        user_message_id: User's message ID (retained, not used)
        task_id: Optional task ID (generated if not provided)
        agent_message_id: Optional agent message ID (generated if not provided)
        
    Returns:
        A2A-compliant response dictionary (Message structure)
    """
    if not task_id:
        # We still need a task_id for the message's 'taskId' field
        task_id = f"task-{str(uuid.uuid4())}"
    
    if not agent_message_id:
        agent_message_id = f"msg-{str(uuid.uuid4())}"
    
    # Build parts structure for response
    response_part = {
        "kind": "text",
        "text": response_text,
        "data": None,
        "file_url": None
    }
    
    # Build the "Message" object (this is the new 'result')
    message_object = {
        "messageId": agent_message_id,
        "role": "agent",
        "parts": [response_part],
        "kind": "message",
        "taskId": task_id,
        "metadata": None,
        "contextId": context_id  # This is the fix to include the contextId
    }
    
    # Return the final JSON-RPC wrapper
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": message_object,  # The 'result' is now the message object
        "error": None
    }


def build_a2a_error_response(
    request_id: str,
    error_code: int,
    error_message: str
) -> Dict[str, Any]:
    """
    Build A2A-compliant error response.
    
    Args:
        request_id: Original request ID
        error_code: JSON-RPC error code
        error_message: Error description
        
    Returns:
        A2A-compliant error response
    """
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": error_code,
            "message": error_message
        }
    }
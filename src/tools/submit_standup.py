""" Handles standup submission with conversational name extraction """

import json
from datetime import date
from google.genai import types
from google.adk.tools import ToolContext
from src.utils import (
    is_within_window,
    get_window_message,
    get_submission_time_wat,
    get_today_wat,
    get_extraction_prompt,
    get_name_extraction_prompt
)
from src.database import has_submitted_today, save_standup_report


async def submit_standup(
    message: str,
    tool_context: ToolContext
) -> str:
    """
    Submit a daily standup report with conversational name extraction.
    
    This function:
    1. Checks if within submission window
    2. Extracts structured data (name, yesterday, today, blockers)
    3. Handles missing name through conversation state
    4. Validates today's plan is present
    5. Saves to database (which automatically invalidates cached summary)
    
    Args:
        message: Raw standup message from user
        tool_context: ADK tool context containing session state
        
    Returns:
        Response message to user
    """
    from google.genai import Client as GenAIClient
    from src.config import GOOGLE_API_KEY, GEMINI_MODEL
    
    # Initialize Gemini client for extraction
    client = GenAIClient(api_key=GOOGLE_API_KEY)
    
    # Check if we have pending standup data from a previous message where name was missing
    pending_standup = tool_context.state.get("pending_standup_data")
    asked_for_name = tool_context.state.get("asked_for_name", False)
    
    if asked_for_name and pending_standup:
        # This is a follow-up message where user is providing their name. Extract name from current message
        name_prompt = get_name_extraction_prompt(message)
        
        try:
            name_response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=name_prompt
            )
            name_text = name_response.text.strip()
            if name_text.startswith('```json'):
                name_text = name_text.replace('```json', '').replace('```', '').strip()
            name_data = json.loads(name_text)
            user_name = name_data.get("user_name")
            
            if not user_name or user_name == "null":
                return "I couldn't extract your name from that. Please tell me your name clearly, like 'I'm John' or 'My name is Sarah'."
            
            # Successfully extracted name - combine with pending standup data
            extracted = {
                "user_name": user_name,
                "yesterday_work": pending_standup.get("yesterday_work"),
                "today_plan": pending_standup.get("today_plan"),
                "blockers": pending_standup.get("blockers"),
                "additional_notes": pending_standup.get("additional_notes")
            }
            
            # Clear the state flags
            tool_context.state["asked_for_name"] = None
            tool_context.state["pending_standup_data"] = None
            
        except Exception as e:
            print(f"Error extracting name: {e}")
            return "I had trouble understanding your name. Please tell me your name clearly."
    else:
        # This is either a first message or a regular standup submission
        extraction_prompt = get_extraction_prompt(message)
        
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=extraction_prompt
            )
            
            response_text = response.text.strip()

            # Clean markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            extracted = json.loads(response_text)
            
        except Exception as e:
            print(f"Error extracting standup data: {e}")
            return "Sorry, I couldn't understand your standup format. Please try again with: 'Hi, I'm [Your Name]. Yesterday I [work]. Today I'm [plan].'"
        
        # Check if name is missing
        user_name = extracted.get("user_name")
        if not user_name or user_name == "null":
            # Store the standup data (without name) and ask for name
            tool_context.state["asked_for_name"] = True
            tool_context.state["pending_standup_data"] = {
                "yesterday_work": extracted.get("yesterday_work"),
                "today_plan": extracted.get("today_plan"),
                "blockers": extracted.get("blockers"),
                "additional_notes": extracted.get("additional_notes")
            }
            return "Thanks for the update! Before I save your standup, I need to know your name. What's your name?"
    
    # At this point, we have extracted data with a name
    user_name = extracted.get("user_name")
    
    if not user_name:
        return "Before I save your standup, I need to know your name. What's your name?"
    
    # Validate today's plan is present. Today's plan is important
    today_plan = extracted.get("today_plan")
    if not today_plan or today_plan == "null":
        return f"""Hi {user_name}! I see what you did yesterday, but I need to know what you're working on TODAY.

Please resubmit your standup including your plan for today."""
    
    # Check time window
    if not is_within_window():
        return get_window_message(user_name)
    
    # Check for duplicate submission
    report_date = get_today_wat()
    
    if await has_submitted_today(user_name, report_date):
        submission_time = get_submission_time_wat().strftime("%I:%M %p WAT")
        return f"""Hey {user_name}!

You've already submitted your standup for today.
I can only accept one submission per person per day.

If you need to make changes, please reach out to your team lead manually.

Want to see today's summary instead?"""
    
    # Save to database
    submitted_at = get_submission_time_wat()
    
    success = await save_standup_report(
        user_name=user_name,
        report_date=report_date,
        submitted_at=submitted_at,
        raw_message=message if not pending_standup else f"Name: {user_name} | Original: {pending_standup}",
        yesterday_work=extracted.get("yesterday_work"),
        today_plan=today_plan,
        blockers=extracted.get("blockers"),
        additional_notes=extracted.get("additional_notes"),
        is_within_window=True
    )
    
    if not success:
        return f"Error saving your standup, {user_name}. Please try again or contact support."
    
    # Build success response
    response = f"""Perfect timing, {user_name}! ✅

I've recorded your standup update:"""
    
    if extracted.get("yesterday_work"):
        response += f"\n• Yesterday: {extracted['yesterday_work']}"
    
    response += f"\n• Today: {today_plan}"
    
    if extracted.get("blockers"):
        response += f"\n• Blockers: {extracted['blockers']}"
    
    response += "\n\nThanks for keeping the team informed!"
    
    return response
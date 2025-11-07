""" Handles user-specific standup summary retrieval with date range support """

import json
from datetime import date, timedelta
from google.genai import types
from src.utils import (
    parse_date_range_query,
    format_date_friendly,
    format_date_range_friendly,
    get_user_names_extraction_prompt
)
from src.database import get_reports_by_users_and_date_range


async def get_user_summary(query: str) -> str:
    """
    Get standup summaries for specific users over a date range.
    
    This function:
    1. Extracts user names from the query using LLM
    2. Parses the date range from the query
    3. Fetches reports for those users in that range
    4. Formats response day-by-day with missing standup indicators
    
    Supports queries like:
    - "Show me Sarah's standup for today"
    - "Get John and Mike's updates for this week"
    - "Sarah's standups for the last 7 days"
    - "What did Bob work on from Monday to Friday?"
    
    Args:
        query: Natural language query mentioning user names and dates
        
    Returns:
        Formatted standup summary for requested users and dates
    """
    from google.genai import Client as GenAIClient
    from src.config import GOOGLE_API_KEY, GEMINI_MODEL
    
    # Initialize Gemini client
    client = GenAIClient(api_key=GOOGLE_API_KEY)
    
    # Step 1: Extract user names from query
    names_prompt = get_user_names_extraction_prompt(query)
    
    try:
        names_response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=names_prompt
        )
        
        names_text = names_response.text.strip()
        if names_text.startswith('```json'):
            names_text = names_text.replace('```json', '').replace('```', '').strip()
        
        names_data = json.loads(names_text)
        user_names = names_data.get("user_names", [])
        
    except Exception as e:
        print(f"Error extracting user names: {e}")
        return "I couldn't identify which team members you're asking about. Please mention their names clearly (e.g., 'Show me Sarah's standup' or 'Get John and Mike's updates')."
    
    if not user_names:
        return "I couldn't identify which team members you're asking about. Please mention their names clearly (e.g., 'Show me Sarah's standup' or 'Get John and Mike's updates')."
    
    # Step 2: Parse date range from query
    try:
        start_date, end_date = parse_date_range_query(query)
    except ValueError as e:
        return f"I couldn't understand the date range. Please try 'today', 'this week', 'last 7 days', or specific dates.\nError: {e}"
    
    # Step 3: Fetch reports for these users in this date range
    reports_by_date = await get_reports_by_users_and_date_range(
        user_names=user_names,
        start_date=start_date,
        end_date=end_date
    )
    
    if not reports_by_date:
        date_range_str = format_date_range_friendly(start_date, end_date)
        user_list = ", ".join(user_names)
        return f"No standup data found for {user_list} during {date_range_str}."
    
    # Step 4: Format the response day-by-day
    date_range_str = format_date_range_friendly(start_date, end_date)
    user_list = ", ".join(user_names) if len(user_names) > 1 else user_names[0]
    
    response = f"# Standup Summary for {user_list}\n"
    response += f"**Period:** {date_range_str}\n\n"
    response += "---\n\n"
    
    # Iterate through each date
    for report_date in sorted(reports_by_date.keys()):
        day_label = format_date_friendly(report_date)
        response += f"## {day_label} ({report_date.strftime('%A')})\n\n"
        
        day_reports = reports_by_date[report_date]
        
        # Show each user's report for this day
        for user_name in user_names:
            report = day_reports.get(user_name)
            
            if report is None:
                # User did not submit for this day
                response += f"**{user_name}:** Did not submit a standup for {report_date.strftime('%B %d, %Y')}\n\n"
            else:
                # User submitted - show their standup
                response += f"**{user_name}:**\n"
                
                if report.get('yesterday_work'):
                    response += f"- **Yesterday:** {report['yesterday_work']}\n"
                
                if report.get('today_plan'):
                    response += f"- **Today:** {report['today_plan']}\n"
                
                if report.get('blockers'):
                    response += f"- **Blockers:** {report['blockers']}\n"
                
                if report.get('additional_notes'):
                    response += f"- **Notes:** {report['additional_notes']}\n"
                
                response += "\n"
        
        response += "---\n\n"
    
    # Add summary statistics
    total_days = (end_date - start_date).days + 1
    total_possible_submissions = len(user_names) * total_days
    
    # Count actual submissions
    actual_submissions = 0
    for day_reports in reports_by_date.values():
        for report in day_reports.values():
            if report is not None:
                actual_submissions += 1
    
    response += f"**Summary Statistics:**\n"
    response += f"- Total Days: {total_days}\n"
    response += f"- Team Members Tracked: {len(user_names)}\n"
    response += f"- Submissions: {actual_submissions} / {total_possible_submissions}\n"
    response += f"- Completion Rate: {(actual_submissions / total_possible_submissions * 100):.1f}%\n"
    
    return response
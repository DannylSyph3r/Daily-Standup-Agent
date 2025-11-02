"""
Get Summary Function Tool
Handles on-demand summary generation with smart caching
"""
import json
from datetime import date
from google.genai import types
from src.utils import (
    parse_date_query,
    format_date_friendly,
    get_summary_prompt,
    get_today_wat,
    get_current_wat_time
)
from src.database import (
    get_daily_reports,
    get_cached_summary,
    cache_summary,
    get_report_count_for_date
)


async def get_summary(query: str, context) -> str:
    """
    Get team standup summary for a specific date.
    
    This function:
    1. Parses the date from natural language query
    2. Checks cache for existing summary
    3. If cache miss: fetches reports, generates summary with LLM, saves to cache
    4. Returns formatted summary
    
    Cache is automatically invalidated when new standups are submitted (via database trigger).
    
    Args:
        query: Natural language date query (e.g., "today", "yesterday", "2025-11-15")
        context: Tool context
        
    Returns:
        Formatted team summary
    """
    from google.genai import Client as GenAIClient
    from src.config import GOOGLE_API_KEY, GEMINI_MODEL
    
    # Initialize Gemini client
    client = GenAIClient(api_key=GOOGLE_API_KEY)
    
    # Step 1: Parse date from query
    try:
        target_date = parse_date_query(query)
    except ValueError as e:
        return f"I couldn't understand the date. Please try 'today', 'yesterday', or a specific date like '2025-11-15'.\nError: {e}"
    
    date_label = format_date_friendly(target_date)
    
    # Step 2: Check cache
    cached = await get_cached_summary(target_date)
    
    if cached:
        # Cache hit - return immediately
        generated_at = cached['generated_at'].strftime("%I:%M %p WAT")
        return f"""# Daily Standup Summary - {date_label}
*Cached from {generated_at} | {cached['total_submissions']} team members reported*

{cached['full_summary']}"""
    
    # Step 3: Cache miss - fetch reports
    reports = await get_daily_reports(target_date)
    
    if not reports:
        today = get_today_wat()
        if target_date == today:
            return f"""No standup reports submitted yet for {date_label}.

The standup window is 9:30 AM - 12:30 PM WAT.
Team members can submit their updates during this window."""
        else:
            return f"No standup reports found for {date_label}."
    
    # Step 4: Generate summary with LLM
    summary_prompt = get_summary_prompt(reports)
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=summary_prompt
        )
        
        summary_text = response.text.strip()
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        # Fallback to basic summary
        summary_text = f"""**Team Updates - {date_label}**

{len(reports)} team members submitted standups:

"""
        for report in reports:
            summary_text += f"""**{report['user_name']}:**
- Today: {report['today_plan']}
"""
            if report.get('blockers'):
                summary_text += f"- Blockers: {report['blockers']}\n"
            
            summary_text += "\n"
    
    # Step 5: Cache the generated summary
    generated_at = get_current_wat_time()
    await cache_summary(
        summary_date=target_date,
        summary_text=summary_text,
        total_submissions=len(reports),
        generated_at=generated_at
    )
    
    # Step 6: Return formatted summary
    return f"""# Daily Standup Summary - {date_label}
*Generated at {generated_at.strftime("%I:%M %p WAT")} | {len(reports)} team members reported*

{summary_text}"""
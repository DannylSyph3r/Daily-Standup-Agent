"""
LLM Prompts for Daily Standup Agent
Structured prompts for data extraction and summary generation
"""


def get_extraction_prompt(raw_message: str) -> str:
    """
    Get prompt for extracting structured standup data from raw message.
    
    Args:
        raw_message: Raw standup message from user
        
    Returns:
        Formatted extraction prompt
    """
    return f"""You are a standup report parser. Extract structured information from the following standup message.

STANDUP MESSAGE:
{raw_message}

Extract the following fields (use null if not mentioned):
- user_name: The person's name (CRITICAL - must be present)
- yesterday_work: What they did yesterday
- today_plan: What they're working on today (CRITICAL - must be present)
- blockers: Any blockers or issues
- additional_notes: Any other notes or comments

Respond ONLY with valid JSON in this exact format:
{{
    "user_name": "name or null",
    "yesterday_work": "text or null",
    "today_plan": "text or null",
    "blockers": "text or null",
    "additional_notes": "text or null"
}}

DO NOT include any explanations, only the JSON object."""


def get_name_extraction_prompt(conversation_history: str) -> str:
    """
    Get prompt for extracting name from conversation history.
    
    Args:
        conversation_history: Full conversation history
        
    Returns:
        Formatted name extraction prompt
    """
    return f"""You are a name extraction specialist. Extract the user's name from this conversation.

CONVERSATION HISTORY:
{conversation_history}

The user either:
1. Mentioned their name in their initial message
2. Provided their name when asked

Extract their name and respond ONLY with valid JSON:
{{
    "user_name": "extracted name or null"
}}

DO NOT include any explanations, only the JSON object."""


def get_summary_prompt(reports: list) -> str:
    """
    Get prompt for generating team summary from reports.
    
    Args:
        reports: List of standup report dictionaries
        
    Returns:
        Formatted summary generation prompt
    """
    # Format reports into a readable structure
    reports_text = ""
    for i, report in enumerate(reports, 1):
        reports_text += f"""
Report #{i} - {report.get('user_name', 'Unknown')}:
- Yesterday: {report.get('yesterday_work', 'Not provided')}
- Today: {report.get('today_plan', 'Not provided')}
- Blockers: {report.get('blockers', 'None')}
- Additional Notes: {report.get('additional_notes', 'None')}
- Submitted at: {report.get('submitted_at', 'Unknown')}
"""
    
    total_reports = len(reports)
    
    return f"""You are an expert engineering manager analyzing daily standup reports.

Here are today's standup submissions ({total_reports} team members reported):
{reports_text}

Generate a comprehensive summary with these sections:

1. **TEAM OVERVIEW**: 2-3 sentences about overall team progress and focus areas
2. **INDIVIDUAL UPDATES**: List each person's update clearly with their name, yesterday's work, today's plan, and blockers
3. **COLLABORATION OPPORTUNITIES**: Identify where team members' work overlaps or where they could help each other
4. **ACTIVE BLOCKERS**: List all blockers with priority assessment (HIGH/MEDIUM/LOW)
5. **INSIGHTS**: Provide 2-3 actionable insights or recommendations for the team lead

Be specific, actionable, and highlight both achievements and concerns.
Format in markdown with clear headers and bullet points.
Use emojis sparingly for visual appeal (🟢 for active work, ⚠️ for blockers, 🤝 for collaboration, 💡 for insights).

Include a header with date and participation rate."""


def get_validation_prompt(extracted_data: dict) -> str:
    """
    Get prompt for validating extracted data completeness.
    
    Args:
        extracted_data: Extracted standup data
        
    Returns:
        Formatted validation prompt
    """
    return f"""Validate this extracted standup data:

{extracted_data}

Check:
1. Is user_name present and not null?
2. Is today_plan present and not null?

Respond ONLY with valid JSON:
{{
    "has_name": true or false,
    "has_today_plan": true or false,
    "is_valid": true or false
}}

DO NOT include any explanations, only the JSON object."""
""" Database Operations for Daily Standup Agent """

from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from src.database.connection import execute_query, fetch_one, fetch_all, fetch_value


async def has_submitted_today(user_name: str, report_date: date) -> bool:
    """
    Check if user already submitted standup for this date.
    
    Args:
        user_name: User's name
        report_date: Date to check
        
    Returns:
        True if already submitted, False otherwise
    """
    query = """
        SELECT EXISTS(
            SELECT 1 FROM standup_reports 
            WHERE user_name = $1 AND report_date = $2
        )
    """
    return await fetch_value(query, user_name, report_date)


async def save_standup_report(
    user_name: str,
    report_date: date,
    submitted_at: datetime,
    raw_message: str,
    yesterday_work: Optional[str],
    today_plan: str,
    blockers: Optional[str],
    additional_notes: Optional[str],
    is_within_window: bool
) -> bool:
    """
    Save a standup report to database.
    
    The database trigger will automatically invalidate any cached summary for this date.
    
    Args:
        user_name: User's name
        report_date: Date of the report
        submitted_at: Submission timestamp
        raw_message: Original message
        yesterday_work: Yesterday's work (optional)
        today_plan: Today's plan (required)
        blockers: Blockers (optional)
        additional_notes: Additional notes (optional)
        is_within_window: Whether submitted within window
        
    Returns:
        True if saved successfully, False if duplicate
    """
    query = """
        INSERT INTO standup_reports 
        (user_name, report_date, submitted_at, yesterday_work, 
         today_plan, blockers, additional_notes, raw_message, is_within_window)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (user_name, report_date) DO NOTHING
        RETURNING report_id
    """
    
    try:
        result = await fetch_value(
            query,
            user_name,
            report_date,
            submitted_at,
            yesterday_work,
            today_plan,
            blockers,
            additional_notes,
            raw_message,
            is_within_window
        )
        return result is not None  # True if inserted, False if duplicate
    except Exception as e:
        print(f"Error saving standup report: {e}")
        return False


async def get_daily_reports(report_date: date) -> List[Dict[str, Any]]:
    """
    Get all standup reports for a specific date.
    
    Args:
        report_date: Date to get reports for
        
    Returns:
        List of report dictionaries
    """
    query = """
        SELECT 
            user_name,
            yesterday_work,
            today_plan,
            blockers,
            additional_notes,
            submitted_at
        FROM standup_reports
        WHERE report_date = $1
        ORDER BY submitted_at ASC
    """
    
    reports = await fetch_all(query, report_date)
    return reports


async def get_reports_by_users_and_date_range(
    user_names: List[str],
    start_date: date,
    end_date: date
) -> Dict[date, Dict[str, Optional[Dict[str, Any]]]]:
    """
    Get standup reports for specific users within a date range.
    
    Returns a nested dictionary structure:
    {
        date1: {
            "user1": {report_data} or None,
            "user2": {report_data} or None,
        },
        date2: {
            "user1": {report_data} or None,
            "user2": {report_data} or None,
        }
    }
    
    Args:
        user_names: List of user names to fetch reports for
        start_date: Start date of range (inclusive)
        end_date: End date of range (inclusive)
        
    Returns:
        Nested dictionary organized by date, then by user
    """
    if not user_names:
        return {}
    
    # Fetch all reports for these users in the date range
    query = """
        SELECT 
            user_name,
            report_date,
            yesterday_work,
            today_plan,
            blockers,
            additional_notes,
            submitted_at
        FROM standup_reports
        WHERE user_name = ANY($1)
        AND report_date >= $2
        AND report_date <= $3
        ORDER BY report_date ASC, submitted_at ASC
    """
    
    reports = await fetch_all(query, user_names, start_date, end_date)
    
    # Build the nested structure
    result = {}
    
    # Generate all dates in range
    current_date = start_date
    while current_date <= end_date:
        result[current_date] = {user: None for user in user_names}
        current_date += timedelta(days=1)
    
    # Fill in the reports
    for report in reports:
        report_date = report['report_date']
        user_name = report['user_name']
        
        if report_date in result and user_name in result[report_date]:
            result[report_date][user_name] = report
    
    return result


async def get_cached_summary(summary_date: date) -> Optional[Dict[str, Any]]:
    """
    Get cached summary if it exists.
    
    Args:
        summary_date: Date to get summary for
        
    Returns:
        Summary dict with full_summary, total_submissions, and generated_at, or None
    """
    query = """
        SELECT 
            full_summary,
            total_submissions,
            generated_at
        FROM daily_summaries
        WHERE summary_date = $1
    """
    
    return await fetch_one(query, summary_date)


async def cache_summary(
    summary_date: date,
    summary_text: str,
    total_submissions: int,
    generated_at: datetime
) -> None:
    """
    Cache a generated summary for quick retrieval.
    
    Args:
        summary_date: Date of the summary
        summary_text: Full summary text
        total_submissions: Number of submissions in summary
        generated_at: When the summary was generated
    """
    query = """
        INSERT INTO daily_summaries 
        (summary_date, full_summary, total_submissions, generated_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (summary_date) DO UPDATE
        SET 
            full_summary = $2,
            total_submissions = $3,
            generated_at = $4
    """
    
    await execute_query(query, summary_date, summary_text, total_submissions, generated_at)


async def get_report_count_for_date(report_date: date) -> int:
    """
    Get count of reports for a specific date.
    
    Args:
        report_date: Date to count reports for
        
    Returns:
        Number of reports
    """
    query = """
        SELECT COUNT(*) 
        FROM standup_reports 
        WHERE report_date = $1
    """
    
    count = await fetch_value(query, report_date)
    return count or 0
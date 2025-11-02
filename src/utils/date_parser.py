"""
Date Parsing Utilities for Daily Standup Agent
Handles parsing of natural language date queries
"""
from datetime import datetime, date, timedelta
import re
import pytz
from src.config import TIMEZONE


WAT = pytz.timezone(TIMEZONE)


def get_today_wat() -> date:
    """Get today's date in WAT timezone."""
    return datetime.now(WAT).date()


def parse_date_query(query: str) -> date:
    """
    Parse a date from natural language query.
    
    Supports:
    - "today" → current date
    - "yesterday" → current date - 1 day
    - "day before yesterday" → current date - 2 days
    - "YYYY-MM-DD" → explicit date
    - "last Friday" → calculate last Friday
    
    Args:
        query: Natural language date query
        
    Returns:
        Parsed date object
        
    Raises:
        ValueError: If date cannot be parsed
    """
    query_lower = query.lower().strip()
    today = get_today_wat()
    
    # Handle "today"
    if "today" in query_lower:
        return today
    
    # Handle "yesterday"
    if "yesterday" in query_lower and "day before yesterday" not in query_lower:
        return today - timedelta(days=1)
    
    # Handle "day before yesterday"
    if "day before yesterday" in query_lower:
        return today - timedelta(days=2)
    
    # Handle explicit date formats (YYYY-MM-DD)
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    date_match = re.search(date_pattern, query)
    if date_match:
        date_str = date_match.group()
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")
    
    # Handle "last [day of week]"
    days_of_week = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    for day_name, day_num in days_of_week.items():
        if f"last {day_name}" in query_lower:
            # Calculate days back to the last occurrence of that day
            days_back = (today.weekday() - day_num) % 7
            if days_back == 0:
                days_back = 7  # If today is that day, go back a week
            return today - timedelta(days=days_back)
    
    # Handle "N days ago"
    days_ago_pattern = r'(\d+)\s+days?\s+ago'
    days_ago_match = re.search(days_ago_pattern, query_lower)
    if days_ago_match:
        days = int(days_ago_match.group(1))
        return today - timedelta(days=days)
    
    # Default: assume today if no specific date mentioned
    return today


def format_date_friendly(target_date: date) -> str:
    """
    Format a date in a friendly way.
    
    Args:
        target_date: Date to format
        
    Returns:
        Friendly formatted string (e.g., "Today", "Yesterday", "November 15, 2025")
    """
    today = get_today_wat()
    
    if target_date == today:
        return "Today"
    elif target_date == today - timedelta(days=1):
        return "Yesterday"
    elif target_date == today - timedelta(days=2):
        return "Day Before Yesterday"
    else:
        return target_date.strftime("%B %d, %Y")
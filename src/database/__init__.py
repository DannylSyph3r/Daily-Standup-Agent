"""
Database package for Daily Standup Agent
Connection management and database operations
"""

from .connection import (
    create_pool,
    get_pool,
    close_pool,
    execute_query,
    fetch_one,
    fetch_all,
    fetch_value
)

from .operations import (
    has_submitted_today,
    save_standup_report,
    get_daily_reports,
    get_cached_summary,
    cache_summary,
    get_report_count_for_date,
    get_reports_by_users_and_date_range
)

__all__ = [
    'create_pool',
    'get_pool',
    'close_pool',
    'execute_query',
    'fetch_one',
    'fetch_all',
    'fetch_value',
    'has_submitted_today',
    'save_standup_report',
    'get_daily_reports',
    'get_cached_summary',
    'cache_summary',
    'get_report_count_for_date',
    'get_reports_by_users_and_date_range'
]
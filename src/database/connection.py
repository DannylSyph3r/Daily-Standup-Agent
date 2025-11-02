"""
Database Connection Management
Handles PostgreSQL connection pooling with asyncpg
"""
import asyncpg
from typing import Optional
from src.config import DATABASE_URL


# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def create_pool() -> asyncpg.Pool:
    """
    Create database connection pool.
    
    Returns:
        asyncpg connection pool
    """
    global _pool
    
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        print("✓ Database connection pool created")
    
    return _pool


async def get_pool() -> asyncpg.Pool:
    """
    Get existing pool or create new one.
    
    Returns:
        asyncpg connection pool
    """
    if _pool is None:
        return await create_pool()
    return _pool


async def close_pool():
    """Close database connection pool."""
    global _pool
    
    if _pool is not None:
        await _pool.close()
        _pool = None
        print("✓ Database connection pool closed")


async def execute_query(query: str, *args):
    """
    Execute a query that doesn't return results (INSERT, UPDATE, DELETE).
    
    Args:
        query: SQL query string
        *args: Query parameters
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args) -> Optional[dict]:
    """
    Fetch a single row.
    
    Args:
        query: SQL query string
        *args: Query parameters
        
    Returns:
        Dict representing the row, or None
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> list:
    """
    Fetch multiple rows.
    
    Args:
        query: SQL query string
        *args: Query parameters
        
    Returns:
        List of dicts representing rows
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def fetch_value(query: str, *args):
    """
    Fetch a single value.
    
    Args:
        query: SQL query string
        *args: Query parameters
        
    Returns:
        Single value
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)
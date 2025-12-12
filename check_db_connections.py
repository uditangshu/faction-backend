#!/usr/bin/env python3
"""Check PostgreSQL connection settings and current connections"""

import asyncio
import asyncpg
from app.core.config import settings
import re

async def check_postgres_connections():
    """Check PostgreSQL max_connections and current connections"""
    # Parse DATABASE_URL
    database_url = settings.DATABASE_URL
    
    # Remove sslmode from URL if present
    if "?sslmode=" in database_url or "&sslmode=" in database_url:
        database_url = re.sub(r'[?&]sslmode=\w+', '', database_url)
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            database_url,
            ssl="require"
        )
        
        # Get max_connections
        max_conn = await conn.fetchval("SHOW max_connections")
        print(f"PostgreSQL max_connections: {max_conn}")
        
        # Get current connections
        current_conn = await conn.fetchval(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
        )
        print(f"Current active connections: {current_conn}")
        
        # Get connections by state
        conn_by_state = await conn.fetch(
            """
            SELECT state, count(*) 
            FROM pg_stat_activity 
            WHERE datname = current_database()
            GROUP BY state
            """
        )
        print("\nConnections by state:")
        for row in conn_by_state:
            print(f"  {row['state']}: {row['count']}")
        
        # Get connection info for this application
        app_conn = await conn.fetchval(
            """
            SELECT count(*) 
            FROM pg_stat_activity 
            WHERE application_name = 'faction_backend'
            """
        )
        print(f"\nConnections from 'faction_backend': {app_conn}")
        
        # Recommendations
        print("\n" + "="*50)
        print("RECOMMENDATIONS:")
        print("="*50)
        if int(max_conn) < 250:
            print(f"⚠️  max_connections ({max_conn}) is too low for high RPS")
            print("   Recommended: at least 250 (or higher for production)")
            print("\n   To increase (if you have superuser access):")
            print("   ALTER SYSTEM SET max_connections = 250;")
            print("   (Then restart PostgreSQL)")
        else:
            print(f"✓ max_connections ({max_conn}) is sufficient")
        
        if int(current_conn) > int(max_conn) * 0.8:
            print(f"⚠️  High connection usage: {current_conn}/{max_conn} ({current_conn*100//int(max_conn)}%)")
            print("   Consider increasing max_connections or optimizing queries")
        else:
            print(f"✓ Connection usage is healthy: {current_conn}/{max_conn}")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")
        print("\nMake sure:")
        print("  1. Database is running and accessible")
        print("  2. DATABASE_URL in .env is correct")
        print("  3. You have permission to query pg_stat_activity")

if __name__ == "__main__":
    asyncio.run(check_postgres_connections())


#!/usr/bin/env python3
"""
Database Connection Pool Monitor

Use this script to monitor database connection pool status and verify that
the connection leak fix is working properly.

Usage:
    python monitor_connections.py

This will show:
- Pool size and configuration
- Current checked out connections
- Pool overflow status
- Connection health checks
"""

import asyncio
import time
from app.db.session import engine
from app.core.config import settings


async def monitor_pool_status():
    """Monitor and display database connection pool status"""
    print("🔧 Database Connection Pool Monitor")
    print("=" * 50)
    print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Hidden'}")
    print(f"Pool Size: {engine.pool.size()}")
    print(f"Max Overflow: {engine.pool._max_overflow}")
    print("=" * 50)
    print()
    
    try:
        while True:
            # Get current pool status
            pool = engine.pool
            
            # Current status
            size = pool.size()
            checked_out = pool.checkedout()
            overflow = pool.overflow()
            checked_in = pool.checkedin()
            
            # Calculate utilization
            total_available = size + overflow
            utilization = (checked_out / total_available * 100) if total_available > 0 else 0
            
            # Status indicator
            if utilization < 50:
                status = "🟢 HEALTHY"
            elif utilization < 80:
                status = "🟡 MODERATE"
            else:
                status = "🔴 HIGH USAGE"
            
            # Display current status
            timestamp = time.strftime("%H:%M:%S")
            print(f"\r[{timestamp}] {status} | "
                  f"Checked Out: {checked_out:2d}/{total_available} "
                  f"({utilization:5.1f}%) | "
                  f"Available: {checked_in:2d} | "
                  f"Overflow: {overflow:2d}", end="", flush=True)
            
            # Warning if too many connections are checked out
            if utilization > 90:
                print(f"\n⚠️  WARNING: Very high connection usage! ({utilization:.1f}%)")
                print("   This might indicate a connection leak.")
                
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n✅ Monitor stopped")
        print("\nConnection Pool Summary:")
        print(f"  Final checked out: {engine.pool.checkedout()}")
        print(f"  Final available: {engine.pool.checkedin()}")
        print(f"  Pool size: {engine.pool.size()}")


async def test_connection():
    """Test a single database connection"""
    print("🧪 Testing database connection...")
    
    try:
        from app.db.session import get_db_session
        
        async for session in get_db_session():
            # Simple query to test connection
            result = await session.execute("SELECT 1 as test")
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ Database connection test successful")
                return True
            else:
                print("❌ Database connection test failed")
                return False
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False


async def main():
    """Main function"""
    print("Starting database connection monitoring...\n")
    
    # Test connection first
    connection_ok = await test_connection()
    if not connection_ok:
        print("❌ Unable to connect to database. Check your configuration.")
        return
    
    print("\n🔍 Starting real-time connection pool monitoring...")
    print("Press Ctrl+C to stop monitoring\n")
    
    await monitor_pool_status()


if __name__ == "__main__":
    asyncio.run(main())

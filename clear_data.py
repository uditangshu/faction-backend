"""Script to clear all data from database tables (keeps schema intact)"""

import asyncio
from sqlalchemy import text
from app.db.session import engine


async def clear_all_data():
    """Clear all data from all tables"""
    async with engine.begin() as conn:
        print("🗑️  Clearing all data from database...")
        
        # Get all table names
        result = await conn.execute(
            text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename != 'alembic_version'
                ORDER BY tablename
            """)
        )
        tables = [row[0] for row in result]
        
        if not tables:
            print("No tables found")
            return
        
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
        
        # Disable foreign key checks and truncate all tables
        print("\n🔄 Truncating tables...")
        for table in tables:
            await conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
            print(f"  ✓ Cleared {table}")
        
        print("\n✅ All data cleared successfully!")
        print("📝 Database schema is intact - only data was removed")


async def clear_specific_table(table_name: str):
    """Clear data from a specific table"""
    async with engine.begin() as conn:
        await conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
        print(f"✅ Cleared data from {table_name}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Clear specific table
        table_name = sys.argv[1]
        asyncio.run(clear_specific_table(table_name))
    else:
        # Clear all tables
        asyncio.run(clear_all_data())


"""Script to delete all users from the database"""

import asyncio
from sqlalchemy import text
from app.db.session import engine


async def delete_all_users():
    """Delete all records from the users table"""
    async with engine.begin() as conn:
        print("🗑️  Deleting all users from the database...")
        
        # Using TRUNCATE is much faster than DELETE for clearing a whole table
        # CASCADE will also remove related records in other tables (e.g., sessions, streaks)
        await conn.execute(text('TRUNCATE TABLE "users" CASCADE'))
        
        # Verify the table is empty
        result = await conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar_one()
        
        if count == 0:
            print(" All users deleted successfully!")
            print(" The 'users' table is now empty, but the table schema remains.")
        else:
            print(f"  Verification failed. {count} users still remain.")


if __name__ == "__main__":
    asyncio.run(delete_all_users())


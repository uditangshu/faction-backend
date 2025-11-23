"""
Example: How to delete data in an Alembic migration

To create a data migration:
1. Generate empty migration: alembic revision -m "clear user data"
2. Edit the generated file to add data operations
"""

# Example migration file content:

def upgrade() -> None:
    """Delete data during upgrade"""
    
    # Delete all records from users table
    op.execute("DELETE FROM users")
    
    # Delete specific records
    op.execute("DELETE FROM users WHERE is_active = false")
    
    # Truncate table (faster, resets sequences)
    op.execute("TRUNCATE TABLE users CASCADE")
    
    # Multiple tables
    op.execute("TRUNCATE TABLE users, user_sessions, otp_verifications CASCADE")


def downgrade() -> None:
    """
    WARNING: Data deletions are NOT reversible!
    You cannot restore deleted data in downgrade()
    """
    pass  # Cannot undo data deletion


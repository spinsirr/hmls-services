import asyncio
import asyncpg

async def run_migration():
    # Connect to the database with hardcoded values for Docker environment
    conn = await asyncpg.connect(
        host="postgres",
        port="5432",
        user="postgres",
        password="postgres",
        database="auth_db"
    )
    
    try:
        # Check if the column already exists
        column_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'is_admin'
            );
            """
        )
        
        if not column_exists:
            print("Adding is_admin column to users table...")
            # Add the is_admin column with a default value of false
            await conn.execute(
                """
                ALTER TABLE users 
                ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE;
                """
            )
            print("Migration completed successfully!")
        else:
            print("Column is_admin already exists in users table. No migration needed.")
    
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        # Close the connection
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration()) 
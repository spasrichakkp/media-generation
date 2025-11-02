"""Test asyncpg connection directly."""

import asyncio
import asyncpg

async def main():
    print("Testing asyncpg connection...")
    print(f"Host: localhost")
    print(f"Port: 5432")
    print(f"User: postgres")
    print(f"Database: media_generation")
    print()

    # First, try connecting to postgres database
    try:
        print("Step 1: Connecting to 'postgres' database...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='postgres'
        )
        print("✅ Connected to 'postgres' database successfully!")

        # List databases
        databases = await conn.fetch("SELECT datname FROM pg_database WHERE datname = 'media_generation'")
        print(f"✅ Found databases: {databases}")

        await conn.close()
    except Exception as e:
        print(f"❌ Connection to 'postgres' database failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Now try connecting to media_generation
    try:
        print("\nStep 2: Connecting to 'media_generation' database...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='media_generation'
        )
        print("✅ Connected to 'media_generation' database successfully!")

        # Test query
        result = await conn.fetchval('SELECT 1')
        print(f"✅ Query result: {result}")

        await conn.close()
    except Exception as e:
        print(f"❌ Connection to 'media_generation' database failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())


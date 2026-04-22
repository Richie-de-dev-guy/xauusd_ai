import asyncio
import os
from sqlalchemy import text
from api.database import engine

async def patch_database():
    print("🔄 Connecting to sentinel.db using bot engine...")
    try:
        async with engine.begin() as conn:
            # We use a raw SQL text update to bypass ORM mapping issues
            await conn.execute(text("""
                UPDATE subscribers 
                SET api_key = 'Effiom3009', 
                    email = 'richmondhenshaw35@gmail.com',
                    is_active = 1
                WHERE id = 1
            """))
            print("✅ UPDATE SUCCESSFUL: Subscriber #1 credentials updated.")
            
            # Double check
            result = await conn.execute(text("SELECT email, api_key FROM subscribers WHERE id = 1"))
            row = result.fetchone()
            print(f"📡 Current DB State: Email: {row[0]} | API Key: {row[1]}")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 TIP: Make sure you are running this from the main project folder.")

if __name__ == "__main__":
    asyncio.run(patch_database())
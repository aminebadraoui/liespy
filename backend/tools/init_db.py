import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from db.session import engine
from sqlmodel import SQLModel
from db.models import User, Scan

async def init_db():
    print("Creating tables...")
    async with engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # Optional: Reset DB
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())

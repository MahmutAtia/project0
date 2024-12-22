import os
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from beanie import init_beanie
from models.resumes import Resume
import asyncio
from contextlib import asynccontextmanager

class MongoDB:
    def __init__(self, mongo_url: str, db_name: str):
        self.mongo_url = mongo_url
        self.db_name = db_name
        self.client = None
        self.db = None

    async def initialize(self):
        """Initialize MongoDB and Beanie"""
        if not self.client:
            self.client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.client[self.db_name]
            # Initialize Beanie with the database
            await init_beanie(
                database=self.db,
                document_models=[Resume]
            )
            print(f"Connected to MongoDB and initialized Beanie: {self.db_name}")

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

    async def get_db(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if not self.db:
            await self.initialize()
        return self.db

# Dependency for FastAPI
async def get_database() -> AsyncIOMotorDatabase:
    MONGOURI = os.environ.get("MONGO_DETAILS")
    MONGODB = os.environ.get("MONGO_DB_NAME")
    db = MongoDB(mongo_url=MONGOURI, db_name=MONGODB)
    # Initialize MongoDB and Beanie

    await db.initialize()
    return db.db



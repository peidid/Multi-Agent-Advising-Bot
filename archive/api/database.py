"""
MongoDB Atlas connection and database setup.
"""
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    sync_client: Optional[MongoClient] = None

    @classmethod
    def get_connection_string(cls) -> str:
        """Get MongoDB connection string from environment."""
        mongo_uri = os.getenv("MONGODB_URI")
        if mongo_uri:
            return mongo_uri

        # Build from components if URI not provided
        host = os.getenv("MONGODB_HOST", "localhost")
        port = os.getenv("MONGODB_PORT", "27017")
        username = os.getenv("MONGODB_USERNAME", "")
        password = os.getenv("MONGODB_PASSWORD", "")

        if username and password:
            return f"mongodb+srv://{username}:{password}@{host}/?retryWrites=true&w=majority"
        return f"mongodb://{host}:{port}"

    @classmethod
    async def connect(cls) -> AsyncIOMotorDatabase:
        """Connect to MongoDB Atlas (async)."""
        if cls.db is not None:
            return cls.db

        connection_string = cls.get_connection_string()
        db_name = os.getenv("MONGODB_DATABASE", "advising_bot")

        try:
            cls.client = AsyncIOMotorClient(
                connection_string,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                serverSelectionTimeoutMS=5000
            )
            cls.db = cls.client[db_name]

            # Verify connection
            await cls.client.admin.command("ping")
            logger.info(f"Connected to MongoDB Atlas: {db_name}")

            # Create indexes
            await cls._create_indexes()

            return cls.db

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def _create_indexes(cls):
        """Create database indexes for performance."""
        if cls.db is None:
            return

        # Users collection indexes
        await cls.db.users.create_index("email", unique=True)
        await cls.db.users.create_index("student_id", sparse=True)

        # Student profiles indexes
        await cls.db.student_profiles.create_index("user_id", unique=True)
        await cls.db.student_profiles.create_index("andrew_id", sparse=True)

        # Conversations indexes
        await cls.db.conversations.create_index("user_id")
        await cls.db.conversations.create_index("created_at")
        await cls.db.conversations.create_index([("user_id", 1), ("is_active", 1)])

        # Sessions indexes
        await cls.db.sessions.create_index("user_id")
        await cls.db.sessions.create_index("token_hash", unique=True)
        await cls.db.sessions.create_index("expires_at", expireAfterSeconds=0)

        # Audit log indexes
        await cls.db.audit_logs.create_index("user_id")
        await cls.db.audit_logs.create_index("timestamp")
        await cls.db.audit_logs.create_index([("action", 1), ("timestamp", -1)])

        logger.info("Database indexes created")

    @classmethod
    async def disconnect(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("Disconnected from MongoDB")

    @classmethod
    def get_sync_client(cls) -> MongoClient:
        """Get synchronous MongoDB client (for non-async contexts)."""
        if cls.sync_client is None:
            connection_string = cls.get_connection_string()
            cls.sync_client = MongoClient(connection_string)
        return cls.sync_client

    @classmethod
    async def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance, connecting if needed."""
        if cls.db is None:
            await cls.connect()
        return cls.db


# Collection names
USERS_COLLECTION = "users"
PROFILES_COLLECTION = "student_profiles"
CONVERSATIONS_COLLECTION = "conversations"
SESSIONS_COLLECTION = "sessions"
AUDIT_LOGS_COLLECTION = "audit_logs"


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency for FastAPI routes."""
    return await MongoDB.get_db()

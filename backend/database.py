"""
MongoDB Atlas connection for user data storage.
Simplified for Railway deployment.
"""
import os
import ssl
import certifi
from datetime import datetime
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
import logging

# Load .env file
from dotenv import load_dotenv
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BACKEND_DIR, '.env'))

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls) -> AsyncIOMotorDatabase:
        """Connect to MongoDB Atlas."""
        if cls.db is not None:
            return cls.db

        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            raise ValueError("MONGODB_URI environment variable is required")

        db_name = os.getenv("MONGODB_DATABASE", "advising_bot")

        logger.info(f"Connecting to MongoDB...")

        # For mongodb+srv:// URIs, TLS is automatic
        # Use minimal configuration - let the driver handle SSL
        cls.client = AsyncIOMotorClient(
            mongo_uri,
            serverSelectionTimeoutMS=30000,
            tlsCAFile=certifi.where()
        )

        # Test connection
        await cls.client.admin.command("ping")
        cls.db = cls.client[db_name]
        logger.info(f"Connected to MongoDB database: {db_name}")

        # Create indexes
        await cls._create_indexes()

        return cls.db

    @classmethod
    async def _create_indexes(cls):
        """Create database indexes."""
        if cls.db is None:
            return

        # Users
        await cls.db.users.create_index("email", unique=True)

        # Conversations
        await cls.db.conversations.create_index("user_id")
        await cls.db.conversations.create_index([("user_id", 1), ("created_at", -1)])

        # Messages
        await cls.db.messages.create_index("conversation_id")
        await cls.db.messages.create_index([("conversation_id", 1), ("timestamp", 1)])

    @classmethod
    async def disconnect(cls):
        """Close connection."""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None

    @classmethod
    async def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database, connecting if needed."""
        if cls.db is None:
            await cls.connect()
        return cls.db


# =============================================================================
# User Operations
# =============================================================================

async def create_user(email: str, name: str, password_hash: str) -> Dict[str, Any]:
    """Create a new user."""
    db = await MongoDB.get_db()

    user_doc = {
        "email": email,
        "name": name,
        "password_hash": password_hash,
        "created_at": datetime.utcnow(),
        "profile": {
            "major": None,
            "minors": [],
            "gpa": None,
            "completed_courses": [],
            "interests": []
        }
    }

    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = str(result.inserted_id)
    return user_doc


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    db = await MongoDB.get_db()
    user = await db.users.find_one({"email": email})
    if user:
        user["_id"] = str(user["_id"])
    return user


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    db = await MongoDB.get_db()
    if not ObjectId.is_valid(user_id):
        return None
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
    return user


async def update_user_profile(user_id: str, profile: Dict[str, Any]) -> bool:
    """Update user's academic profile."""
    db = await MongoDB.get_db()
    if not ObjectId.is_valid(user_id):
        return False

    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"profile": profile, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0


# =============================================================================
# Conversation Operations
# =============================================================================

async def create_conversation(user_id: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Create a new conversation."""
    db = await MongoDB.get_db()

    conv_doc = {
        "user_id": user_id,
        "title": title or "New Conversation",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "message_count": 0
    }

    result = await db.conversations.insert_one(conv_doc)
    conv_doc["_id"] = str(result.inserted_id)
    return conv_doc


async def get_conversations(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get user's conversations."""
    db = await MongoDB.get_db()

    cursor = db.conversations.find(
        {"user_id": user_id}
    ).sort("updated_at", -1).limit(limit)

    conversations = []
    async for conv in cursor:
        conv["_id"] = str(conv["_id"])
        conversations.append(conv)

    return conversations


async def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Get a conversation by ID."""
    db = await MongoDB.get_db()
    if not ObjectId.is_valid(conversation_id):
        return None

    conv = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
    if conv:
        conv["_id"] = str(conv["_id"])
    return conv


async def update_conversation_title(conversation_id: str, title: str) -> bool:
    """Update conversation title."""
    db = await MongoDB.get_db()
    if not ObjectId.is_valid(conversation_id):
        return False

    result = await db.conversations.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"title": title, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0


async def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation and its messages."""
    db = await MongoDB.get_db()
    if not ObjectId.is_valid(conversation_id):
        return False

    # Delete messages first
    await db.messages.delete_many({"conversation_id": conversation_id})

    # Delete conversation
    result = await db.conversations.delete_one({"_id": ObjectId(conversation_id)})
    return result.deleted_count > 0


# =============================================================================
# Message Operations
# =============================================================================

async def add_message(
    conversation_id: str,
    role: str,  # "user" or "assistant"
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Add a message to a conversation."""
    db = await MongoDB.get_db()

    msg_doc = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow(),
        "metadata": metadata or {}
    }

    result = await db.messages.insert_one(msg_doc)
    msg_doc["_id"] = str(result.inserted_id)

    # Update conversation
    await db.conversations.update_one(
        {"_id": ObjectId(conversation_id)},
        {
            "$set": {"updated_at": datetime.utcnow()},
            "$inc": {"message_count": 1}
        }
    )

    return msg_doc


async def get_messages(conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get messages from a conversation."""
    db = await MongoDB.get_db()

    cursor = db.messages.find(
        {"conversation_id": conversation_id}
    ).sort("timestamp", 1).limit(limit)

    messages = []
    async for msg in cursor:
        msg["_id"] = str(msg["_id"])
        messages.append(msg)

    return messages

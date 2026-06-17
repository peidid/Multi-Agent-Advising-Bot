"""
User service for CRUD operations.
"""
from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.models.user import User, UserCreate, UserUpdate, UserInDB
from api.services.auth_service import AuthService
from api.database import USERS_COLLECTION


class UserService:
    """Service for user operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[USERS_COLLECTION]

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if email already exists
        existing = await self.collection.find_one({"email": user_data.email})
        if existing:
            raise ValueError("User with this email already exists")

        # Hash password
        hashed_password = AuthService.hash_password(user_data.password)

        # Create user document
        user_doc = {
            "email": user_data.email,
            "full_name": user_data.full_name,
            "student_id": user_data.student_id,
            "is_active": user_data.is_active,
            "role": user_data.role,
            "hashed_password": hashed_password,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None,
            "preferences": {}
        }

        result = await self.collection.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)

        return User(
            id=str(result.inserted_id),
            email=user_doc["email"],
            full_name=user_doc["full_name"],
            student_id=user_doc["student_id"],
            is_active=user_doc["is_active"],
            role=user_doc["role"],
            created_at=user_doc["created_at"],
            updated_at=user_doc["updated_at"],
            last_login=user_doc["last_login"],
            preferences=user_doc["preferences"]
        )

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        if not ObjectId.is_valid(user_id):
            return None

        user_doc = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            return None

        return User(
            id=str(user_doc["_id"]),
            email=user_doc["email"],
            full_name=user_doc["full_name"],
            student_id=user_doc.get("student_id"),
            is_active=user_doc["is_active"],
            role=user_doc["role"],
            created_at=user_doc["created_at"],
            updated_at=user_doc["updated_at"],
            last_login=user_doc.get("last_login"),
            preferences=user_doc.get("preferences", {})
        )

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email (includes password hash)."""
        user_doc = await self.collection.find_one({"email": email})
        if not user_doc:
            return None

        return UserInDB(
            _id=str(user_doc["_id"]),
            email=user_doc["email"],
            full_name=user_doc["full_name"],
            student_id=user_doc.get("student_id"),
            is_active=user_doc["is_active"],
            role=user_doc["role"],
            hashed_password=user_doc["hashed_password"],
            created_at=user_doc["created_at"],
            updated_at=user_doc["updated_at"],
            last_login=user_doc.get("last_login"),
            preferences=user_doc.get("preferences", {})
        )

    async def update_user(self, user_id: str, update_data: UserUpdate) -> Optional[User]:
        """Update user fields."""
        if not ObjectId.is_valid(user_id):
            return None

        # Build update document
        update_doc = {"updated_at": datetime.utcnow()}

        if update_data.email is not None:
            update_doc["email"] = update_data.email
        if update_data.full_name is not None:
            update_doc["full_name"] = update_data.full_name
        if update_data.student_id is not None:
            update_doc["student_id"] = update_data.student_id
        if update_data.is_active is not None:
            update_doc["is_active"] = update_data.is_active
        if update_data.role is not None:
            update_doc["role"] = update_data.role
        if update_data.password is not None:
            update_doc["hashed_password"] = AuthService.hash_password(update_data.password)

        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_doc}
        )

        if result.modified_count == 0:
            return None

        return await self.get_user_by_id(user_id)

    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        if ObjectId.is_valid(user_id):
            await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_login": datetime.utcnow()}}
            )

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user (soft delete - sets is_active to False)."""
        if not ObjectId.is_valid(user_id):
            return False

        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )

        return result.modified_count > 0

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[str] = None,
        active_only: bool = True
    ) -> List[User]:
        """List users with optional filtering."""
        query = {}
        if active_only:
            query["is_active"] = True
        if role:
            query["role"] = role

        cursor = self.collection.find(query).skip(skip).limit(limit)
        users = []

        async for user_doc in cursor:
            users.append(User(
                id=str(user_doc["_id"]),
                email=user_doc["email"],
                full_name=user_doc["full_name"],
                student_id=user_doc.get("student_id"),
                is_active=user_doc["is_active"],
                role=user_doc["role"],
                created_at=user_doc["created_at"],
                updated_at=user_doc["updated_at"],
                last_login=user_doc.get("last_login"),
                preferences=user_doc.get("preferences", {})
            ))

        return users

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user_in_db = await self.get_user_by_email(email)

        if not user_in_db:
            return None

        if not user_in_db.is_active:
            return None

        if not AuthService.verify_password(password, user_in_db.hashed_password):
            return None

        # Update last login
        await self.update_last_login(user_in_db.id)

        return User(
            id=user_in_db.id,
            email=user_in_db.email,
            full_name=user_in_db.full_name,
            student_id=user_in_db.student_id,
            is_active=user_in_db.is_active,
            role=user_in_db.role,
            created_at=user_in_db.created_at,
            updated_at=user_in_db.updated_at,
            last_login=datetime.utcnow(),
            preferences=user_in_db.preferences
        )

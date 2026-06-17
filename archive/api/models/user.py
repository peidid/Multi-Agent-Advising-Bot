"""
User models for MongoDB storage.
Handles authentication and user management.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId


class PyObjectId(str):
    """Custom ObjectId type for Pydantic v2."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, handler):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError("Invalid ObjectId")


class UserBase(BaseModel):
    """Base user model with common fields."""
    email: EmailStr
    full_name: str
    student_id: Optional[str] = None  # CMU Andrew ID
    is_active: bool = True
    role: str = "student"  # student, advisor, admin


class UserCreate(UserBase):
    """Model for creating a new user."""
    password: str


class UserUpdate(BaseModel):
    """Model for updating user fields."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    student_id: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
    password: Optional[str] = None


class UserInDB(UserBase):
    """User model as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    # User preferences
    preferences: dict = Field(default_factory=dict)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class User(UserBase):
    """User model for API responses (no password)."""
    id: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    preferences: dict = Field(default_factory=dict)

    model_config = {
        "from_attributes": True
    }


class UserLogin(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Data encoded in JWT token."""
    user_id: str
    email: str
    role: str
    exp: datetime

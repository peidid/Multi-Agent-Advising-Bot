"""
Session models for managing user sessions.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SessionBase(BaseModel):
    """Base session model."""
    user_id: str
    is_active: bool = True


class SessionCreate(SessionBase):
    """Model for creating a new session."""
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class Session(SessionBase):
    """Full session as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")

    # Session token (hashed)
    token_hash: str

    # Client info
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=7)
    )
    last_activity: datetime = Field(default_factory=datetime.utcnow)

    # Session data (for caching)
    cached_profile: Optional[Dict[str, Any]] = None

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }


class SessionInfo(BaseModel):
    """Session info for API responses."""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    is_active: bool

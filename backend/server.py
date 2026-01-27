"""
FastAPI Backend Server for Multi-Agent Advising System.
Connects to MongoDB Atlas and serves the Next.js frontend.
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
import logging

# Add parent directory to path for imports
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, BACKEND_DIR)

# Load .env from backend folder
from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, '.env'))

from database import (
    MongoDB,
    create_user, get_user_by_email, get_user_by_id, update_user_profile,
    create_conversation, get_conversations, get_conversation,
    update_conversation_title, delete_conversation,
    add_message, get_messages
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
import hashlib
security = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


# =============================================================================
# Pydantic Models
# =============================================================================

class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    major: Optional[str] = None
    minors: List[str] = []
    gpa: Optional[float] = None
    completed_courses: List[str] = []
    interests: List[str] = []


class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    agents_used: List[str] = []
    workflow_details: Optional[Dict[str, Any]] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = None


# =============================================================================
# Auth Helpers
# =============================================================================

def hash_password(password: str) -> str:
    """Simple SHA256 hash with salt for password storage."""
    salted = password + SECRET_KEY
    return hashlib.sha256(salted.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    return hash_password(plain) == hashed


def create_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# =============================================================================
# Multi-Agent Runner
# =============================================================================

class AgentRunner:
    """Runs the multi-agent workflow."""

    def __init__(self):
        self._app = None

    def _get_app(self):
        if self._app is None:
            from multi_agent import app
            self._app = app
        return self._app

    async def run(
        self,
        query: str,
        user_profile: Optional[Dict] = None,
        history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Run the multi-agent workflow."""
        from langchain_core.messages import HumanMessage, AIMessage
        from blackboard.schema import WorkflowStep

        app = self._get_app()

        # Build messages
        messages = []
        if history:
            for msg in history[-10:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=query))

        # Initial state
        state = {
            "user_query": query,
            "student_profile": user_profile or {},
            "agent_outputs": {},
            "constraints": [],
            "risks": [],
            "plan_options": [],
            "conflicts": [],
            "open_questions": [],
            "messages": messages,
            "active_agents": [],
            "workflow_step": WorkflowStep.INITIAL,
            "iteration_count": 0,
            "next_agent": None,
            "user_goal": None
        }

        # Run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, app.invoke, state)

        return result


agent_runner = AgentRunner()


# =============================================================================
# FastAPI App
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    logger.info("Starting server...")
    await MongoDB.connect()
    yield
    logger.info("Shutting down...")
    await MongoDB.disconnect()


app = FastAPI(
    title="Multi-Agent Advising API",
    description="Backend for the academic advising chatbot",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Auth Endpoints
# =============================================================================

@app.post("/api/auth/register")
async def register(data: UserRegister):
    """Register a new user."""
    try:
        existing = await get_user_by_email(data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user = await create_user(
            email=data.email,
            name=data.name,
            password_hash=hash_password(data.password)
        )

        token = create_token(user["_id"], user["email"])

        return {
            "user": {
                "id": user["_id"],
                "email": user["email"],
                "name": user["name"]
            },
            "token": token
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/api/auth/login")
async def login(data: UserLogin):
    """Login and get token."""
    user = await get_user_by_email(data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user["_id"], user["email"])

    return {
        "user": {
            "id": user["_id"],
            "email": user["email"],
            "name": user["name"],
            "profile": user.get("profile", {})
        },
        "token": token
    }


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return {
        "id": user["_id"],
        "email": user["email"],
        "name": user["name"],
        "profile": user.get("profile", {})
    }


@app.put("/api/auth/profile")
async def update_profile(profile: UserProfile, user: dict = Depends(get_current_user)):
    """Update user's academic profile."""
    await update_user_profile(user["_id"], profile.model_dump())
    return {"success": True, "profile": profile.model_dump()}


# =============================================================================
# Conversation Endpoints
# =============================================================================

@app.get("/api/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    """List user's conversations."""
    conversations = await get_conversations(user["_id"])
    return {"conversations": conversations}


@app.post("/api/conversations")
async def new_conversation(
    data: Optional[ConversationCreate] = None,
    user: dict = Depends(get_current_user)
):
    """Create a new conversation."""
    title = data.title if data else None
    conv = await create_conversation(user["_id"], title)
    return conv


@app.get("/api/conversations/{conversation_id}")
async def get_conv(conversation_id: str, user: dict = Depends(get_current_user)):
    """Get a conversation with messages."""
    conv = await get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv["user_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    messages = await get_messages(conversation_id)
    conv["messages"] = messages
    return conv


@app.delete("/api/conversations/{conversation_id}")
async def delete_conv(conversation_id: str, user: dict = Depends(get_current_user)):
    """Delete a conversation."""
    conv = await get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv["user_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    await delete_conversation(conversation_id)
    return {"success": True}


# =============================================================================
# Chat Endpoint
# =============================================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(data: ChatMessage, user: dict = Depends(get_current_user)):
    """Send a message and get AI response."""

    # Get or create conversation
    if data.conversation_id:
        conv = await get_conversation(data.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv["user_id"] != user["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
        conversation_id = data.conversation_id
    else:
        # Create new conversation with first message as title
        title = data.message[:50] + "..." if len(data.message) > 50 else data.message
        conv = await create_conversation(user["_id"], title)
        conversation_id = conv["_id"]

    # Save user message
    await add_message(conversation_id, "user", data.message)

    # Get conversation history
    messages = await get_messages(conversation_id)
    history = [{"role": m["role"], "content": m["content"]} for m in messages]

    # Get user profile for personalization
    profile = user.get("profile", {})
    student_profile = {
        "major": [profile.get("major")] if profile.get("major") else [],
        "minors": profile.get("minors", []),
        "gpa": profile.get("gpa"),
        "completed_courses": profile.get("completed_courses", [])
    }

    # Run multi-agent workflow
    try:
        result = await agent_runner.run(
            query=data.message,
            user_profile=student_profile,
            history=history[:-1]  # Exclude the just-added message
        )
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    # Extract response
    response_text = ""
    if result.get("messages"):
        last_msg = result["messages"][-1]
        response_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # Save assistant response
    agents_used = list(result.get("agent_outputs", {}).keys())
    await add_message(
        conversation_id,
        "assistant",
        response_text,
        metadata={"agents_used": agents_used}
    )

    return ChatResponse(
        conversation_id=conversation_id,
        response=response_text,
        agents_used=agents_used,
        workflow_details={
            "conflicts": len(result.get("conflicts", [])),
            "risks": len(result.get("risks", []))
        }
    )


# =============================================================================
# Health Check
# =============================================================================

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    try:
        db = await MongoDB.get_db()
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Multi-Agent Advising API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)

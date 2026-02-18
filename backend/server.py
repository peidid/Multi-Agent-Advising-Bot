"""
FastAPI Backend Server for Multi-Agent Advising System.
Connects to MongoDB Atlas and serves the Next.js frontend.
"""
import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from threading import Thread
from queue import Queue
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


class CourseTaken(BaseModel):
    code: str
    name: Optional[str] = None
    grade: str
    semester: str
    units: Optional[float] = None


class UserProfile(BaseModel):
    major: Optional[str] = None
    year: Optional[str] = None  # First Year, Sophomore, Junior, Senior
    minors: List[str] = []
    concentration: Optional[str] = None
    gpa: Optional[float] = None
    expected_graduation: Optional[str] = None
    completed_courses: List[str] = []
    courses_taken: List[CourseTaken] = []
    interests: List[str] = []
    career_goals: List[str] = []


class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    planning_mode: bool = False  # Enable collaborative planning mode
    system: str = "multi_agent"  # Which system to use — see /api/systems


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    agents_used: List[str] = []
    workflow_details: Optional[Dict[str, Any]] = None
    execution_stats: Optional[Dict[str, Any]] = None  # Parallel execution stats
    phase_timing: Optional[Dict[str, Any]] = None  # Timing for each phase


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class PlanningRequest(BaseModel):
    """Request to start a collaborative planning session."""
    request: str  # User's planning request
    conversation_id: Optional[str] = None


class PlanningResponse(BaseModel):
    """Response from planning session."""
    session_id: str
    status: str
    total_rounds: int
    final_plan: Optional[Dict[str, Any]] = None
    rounds: List[Dict[str, Any]] = []


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
            "conversation_history": history or [],  # Pass conversation for context
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
            "user_goal": None,
            "execution_metadata": None,
            "phase_timing": {},
            "context_text": ""  # Will be filled by coordinator
        }

        # Run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, app.invoke, state)

        return result


agent_runner = AgentRunner()


# =============================================================================
# Baseline Runners — Ablation Study (ACL 2026)
# =============================================================================

try:
    from baselines.runners import (
        OpaqueMultiAgentRunner,
        OneShotRunner,
        SingleAgentCoTRunner,
        SingleAgentRunner,
    )

    SYSTEM_RUNNERS = {
        # ── Experiment ──────────────────────────────────────────────────────
        # Full system: LLM routing → 4 parallel agents → coordinator
        # evaluation (up to 3 rounds, k=10 re-retrieval) → LLM synthesis.
        # Streaming events emitted → user sees agent reasoning in real time.
        "multi_agent": agent_runner,

        # ── Ablation 1 ──────────────────────────────────────────────────────
        # Identical processing to multi_agent. Streaming events suppressed.
        # User sees only the final answer — no transparency panel.
        # → Tests: does visibility itself change trust / decision quality?
        "multi_agent_opaque": OpaqueMultiAgentRunner(),

        # ── Ablation 2 ──────────────────────────────────────────────────────
        # One GPT-5.2 call. All 5 RAG domains concatenated. No coordinator.
        # No specialisation. Same model and same data as the full system.
        # → Tests: does multi-agent specialisation add value at all?
        "single_agent": SingleAgentRunner(),

        # ── Ablation 3 ──────────────────────────────────────────────────────
        # Same as single_agent + explicit chain-of-thought prompt.
        # → Tests: does CoT within one call match multi-agent negotiation?
        "single_agent_cot": SingleAgentCoTRunner(),

        # ── Ablation 4 ──────────────────────────────────────────────────────
        # LLM routing → parallel agents → LLM synthesis.
        # evaluate_outputs_for_sufficiency() is SKIPPED entirely.
        # → Tests: does the iterative evaluation loop improve quality?
        "one_shot": OneShotRunner(),
    }
    BASELINES_AVAILABLE = True
    logger.info("✅ Baseline runners loaded: %s", list(SYSTEM_RUNNERS.keys()))
except Exception as _e:
    logger.warning("⚠️  Baseline runners not available: %s", _e)
    SYSTEM_RUNNERS = {"multi_agent": agent_runner}
    BASELINES_AVAILABLE = False


def _get_runner(system: str):
    """Return the runner for the requested system, defaulting to multi_agent."""
    return SYSTEM_RUNNERS.get(system, agent_runner)


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
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler to ensure CORS headers on errors
from fastapi.responses import JSONResponse
from starlette.requests import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure CORS headers are included in error responses."""
    logger.error(f"Unhandled error: {exc}")
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=headers
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
        "year": profile.get("year"),
        "minors": profile.get("minors", []),
        "concentration": profile.get("concentration"),
        "gpa": profile.get("gpa"),
        "expected_graduation": profile.get("expected_graduation"),
        "completed_courses": profile.get("completed_courses", []),
        "courses_taken": profile.get("courses_taken", []),
        "interests": profile.get("interests", []),
        "career_goals": profile.get("career_goals", [])
    }

    # Run the selected system (full multi-agent or a baseline)
    try:
        runner = _get_runner(data.system)
        result = await runner.run(
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

    # Save assistant response with full workflow details for developer analysis
    agents_used = list(result.get("agent_outputs", {}).keys())

    # Extract agent outputs for storage (convert Pydantic models to dicts)
    agent_outputs_data = {}
    for agent_name, output in result.get("agent_outputs", {}).items():
        if hasattr(output, "model_dump"):
            agent_outputs_data[agent_name] = output.model_dump()
        elif hasattr(output, "dict"):
            agent_outputs_data[agent_name] = output.dict()
        else:
            agent_outputs_data[agent_name] = str(output)

    # Extract conflicts for storage
    conflicts_data = []
    for conflict in result.get("conflicts", []):
        if hasattr(conflict, "model_dump"):
            conflicts_data.append(conflict.model_dump())
        elif hasattr(conflict, "dict"):
            conflicts_data.append(conflict.dict())
        else:
            conflicts_data.append(str(conflict))

    # Extract risks for storage
    risks_data = []
    for risk in result.get("risks", []):
        if hasattr(risk, "model_dump"):
            risks_data.append(risk.model_dump())
        elif hasattr(risk, "dict"):
            risks_data.append(risk.dict())
        else:
            risks_data.append(str(risk))

    # Extract execution metadata (parallel execution stats)
    execution_metadata = result.get("execution_metadata", {})
    if execution_metadata and hasattr(execution_metadata, "model_dump"):
        execution_metadata = execution_metadata.model_dump()
    elif execution_metadata and hasattr(execution_metadata, "dict"):
        execution_metadata = execution_metadata.dict()

    # Extract phase timing (for developer analysis)
    phase_timing = result.get("phase_timing", {})

    # Full workflow metadata for developer access
    workflow_metadata = {
        "system": data.system,  # which baseline/experiment was used
        "agents_used": agents_used,
        "agent_outputs": agent_outputs_data,
        "conflicts": conflicts_data,
        "risks": risks_data,
        "workflow_step": str(result.get("workflow_step", "unknown")),
        "iteration_count": result.get("iteration_count", 0),
        "active_agents": result.get("active_agents", []),
        "user_goal": result.get("user_goal", ""),
        # Parallel execution metadata
        "execution_metadata": execution_metadata,
        # Phase timing for performance analysis
        "phase_timing": phase_timing,
    }

    await add_message(
        conversation_id,
        "assistant",
        response_text,
        metadata=workflow_metadata
    )

    return ChatResponse(
        conversation_id=conversation_id,
        response=response_text,
        agents_used=agents_used,
        workflow_details={
            "conflicts": len(conflicts_data),
            "risks": len(risks_data),
            "workflow_step": str(result.get("workflow_step", "unknown")),
            "iteration_count": result.get("iteration_count", 0)
        },
        execution_stats={
            "mode": execution_metadata.get("execution_mode", "unknown") if execution_metadata else "unknown",
            "parallel_time": execution_metadata.get("total_execution_time", 0) if execution_metadata else 0,
            "sequential_equivalent": execution_metadata.get("sequential_equivalent", 0) if execution_metadata else 0,
            "speedup": execution_metadata.get("parallel_speedup", 1.0) if execution_metadata else 1.0,
            "agents_executed": execution_metadata.get("agents_executed", []) if execution_metadata else [],
            "execution_times": execution_metadata.get("execution_times", {}) if execution_metadata else {}
        },
        phase_timing=phase_timing if phase_timing else {
            "intent_classification": 0,
            "parallel_agents": 0,
            "synthesis": 0,
            "total": 0
        }
    )


# =============================================================================
# Planning Result Formatter
# =============================================================================

def _format_planning_result(session) -> str:
    """Format a planning session result as a readable message."""
    lines = []

    # Header
    status_emoji = "✅" if session.status == "completed" else "⚠️"
    lines.append(f"{status_emoji} **Course Planning Complete** ({session.status})")
    lines.append(f"")
    lines.append(f"Negotiation took **{len(session.rounds)} rounds** to reach {'consensus' if session.status == 'completed' else 'maximum rounds'}.")
    lines.append("")

    # Final Plan
    if session.final_plan:
        plan = session.final_plan
        lines.append("## 📋 Your Course Plan")
        lines.append("")
        lines.append(f"**Program:** {plan.program}")
        lines.append(f"**Timeline:** {plan.start_semester} → {plan.target_graduation}")
        lines.append(f"**Total Units:** {plan.total_units}")
        lines.append("")

        lines.append("### Semester Schedule")
        for sem in plan.semesters:
            lines.append(f"")
            lines.append(f"**{sem.semester}** ({sem.total_units} units)")
            lines.append(f"- Courses: {', '.join(sem.courses)}")
            if sem.notes:
                lines.append(f"- Notes: {sem.notes}")

        if plan.requirements_met:
            lines.append("")
            lines.append(f"**Requirements Met:** {', '.join(plan.requirements_met)}")

        if plan.requirements_pending:
            lines.append(f"**Still Needed:** {', '.join(plan.requirements_pending)}")

    # Summary of negotiation
    lines.append("")
    lines.append("---")
    lines.append("### 🤝 Agent Negotiation Summary")

    for round_data in session.rounds:
        round_status = "✅" if round_data.all_approved else "🔄"
        lines.append(f"")
        lines.append(f"**Round {round_data.round_number}** {round_status}")

        for critique in round_data.critiques:
            agent_name = critique.agent_name.replace("_", " ").title()
            status = "✅ Approved" if critique.approved else "⚠️ Needs revision"
            lines.append(f"- {agent_name}: {status}")
            if critique.issues and not critique.approved:
                for issue in critique.issues[:2]:
                    lines.append(f"  - {issue}")

    return "\n".join(lines)


# =============================================================================
# Streaming Chat Endpoint
# =============================================================================

@app.post("/api/chat/stream")
async def chat_stream(data: ChatMessage, user: dict = Depends(get_current_user)):
    """
    Send a message and get streaming response.
    Real-time updates as multi-agent workflow progresses.
    """
    import json

    # Get or create conversation
    if data.conversation_id:
        conv = await get_conversation(data.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv["user_id"] != user["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
        conversation_id = data.conversation_id
    else:
        title = data.message[:50] + "..." if len(data.message) > 50 else data.message
        conv = await create_conversation(user["_id"], title)
        conversation_id = conv["_id"]

    # Save user message
    await add_message(conversation_id, "user", data.message)

    # Get conversation history
    messages = await get_messages(conversation_id)
    history = [{"role": m["role"], "content": m["content"]} for m in messages]

    # Get user profile
    profile = user.get("profile", {})
    student_profile = {
        "major": [profile.get("major")] if profile.get("major") else [],
        "year": profile.get("year"),
        "minors": profile.get("minors", []),
        "concentration": profile.get("concentration"),
        "gpa": profile.get("gpa"),
        "expected_graduation": profile.get("expected_graduation"),
        "completed_courses": profile.get("completed_courses", []),
        "courses_taken": profile.get("courses_taken", []),
        "interests": profile.get("interests", []),
        "career_goals": profile.get("career_goals", [])
    }

    async def generate():
        """Generate SSE stream."""
        # Import streaming infrastructure
        try:
            from streaming.callback import StreamCallbackManager, set_stream_manager
            from streaming.events import workflow_start_event
            streaming_available = True
        except ImportError:
            streaming_available = False

        if streaming_available:
            stream_manager = StreamCallbackManager()
            set_stream_manager(stream_manager)

            # Emit workflow start
            stream_manager.emit(workflow_start_event(data.message))

        # Result container
        workflow_result = {"result": None, "error": None, "planning_session": None}

        def run_workflow():
            try:
                if data.system == "multi_agent":
                    # ── Full transparent system ──────────────────────────────
                    # Runs the complete LangGraph workflow. Streaming events
                    # ARE emitted (stream_manager is already registered above),
                    # so the frontend sees agent cards and coordinator scores
                    # in real time.
                    from langchain_core.messages import HumanMessage, AIMessage
                    from blackboard.schema import WorkflowStep
                    from multi_agent import app as workflow_app

                    msgs = []
                    for msg in history[:-1]:
                        if msg["role"] == "user":
                            msgs.append(HumanMessage(content=msg["content"]))
                        else:
                            msgs.append(AIMessage(content=msg["content"]))
                    msgs.append(HumanMessage(content=data.message))

                    state = {
                        "user_query": data.message,
                        "student_profile": student_profile,
                        "conversation_history": history[:-1],
                        "agent_outputs": {},
                        "constraints": [],
                        "risks": [],
                        "plan_options": [],
                        "conflicts": [],
                        "open_questions": [],
                        "messages": msgs,
                        "active_agents": [],
                        "workflow_step": WorkflowStep.INITIAL,
                        "iteration_count": 0,
                        "next_agent": None,
                        "user_goal": None,
                        "execution_metadata": None,
                        "phase_timing": {},
                        "context_text": "",
                    }
                    result = workflow_app.invoke(state)

                else:
                    # ── Baseline / opaque system ─────────────────────────────
                    # run_sync() is called directly in this thread.
                    # For multi_agent_opaque: it runs the FULL LangGraph
                    # workflow (app.invoke), which internally calls emit_event().
                    # We must deregister the stream_manager BEFORE invoking,
                    # otherwise events would be emitted — defeating the opaque
                    # purpose. The local stream_manager object still receives
                    # mark_done() in the finally block, ending the SSE loop.
                    if data.system == "multi_agent_opaque" and streaming_available:
                        from streaming.callback import set_stream_manager as _ssm
                        _ssm(None)  # suppress all emit_event() calls

                    runner = _get_runner(data.system)
                    result = runner.run_sync(
                        query=data.message,
                        user_profile=student_profile,
                        history=history[:-1],
                    )

                workflow_result["result"] = result
            except Exception as e:
                workflow_result["error"] = str(e)
                logger.error(f"Streaming workflow error: {e}")
            finally:
                if streaming_available:
                    stream_manager.mark_done()

        def run_planning_workflow():
            """Run collaborative planning mode instead of regular workflow."""
            try:
                import asyncio
                from planning.coordinator import PlanningModeCoordinator
                from agents.planning_agent import AcademicPlanningAgent
                from agents.programs_agent import ProgramsRequirementsAgent
                from agents.courses_agent import CourseSchedulingAgent
                from agents.policy_agent import PolicyComplianceAgent

                # Get cached agents
                agents = get_planning_agents()

                # Event emitter for streaming
                def emit_event(event: dict):
                    if streaming_available:
                        stream_manager.emit({
                            "type": event.get("type", "planning_update"),
                            "data": event
                        })

                # Create coordinator with student profile access
                coordinator = PlanningModeCoordinator(
                    planning_agent=agents["planning"],
                    programs_agent=agents["programs"],
                    courses_agent=agents["courses"],
                    policy_agent=agents["policy"],
                    emit_event=emit_event,
                    db=None
                )

                # Add user_id to student_profile
                profile_with_id = {**student_profile, "_id": str(user["_id"])}

                # Run planning session synchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    session = loop.run_until_complete(
                        coordinator.execute_planning_session(
                            user_id=str(user["_id"]),
                            conversation_id=conversation_id,
                            request=data.message,
                            student_profile=profile_with_id
                        )
                    )
                    workflow_result["planning_session"] = session
                finally:
                    loop.close()

            except Exception as e:
                workflow_result["error"] = str(e)
                logger.error(f"Planning workflow error: {e}", exc_info=True)
            finally:
                if streaming_available:
                    stream_manager.mark_done()

        # Run workflow in background (planning or regular)
        if data.planning_mode:
            workflow_thread = Thread(target=run_planning_workflow, daemon=True)
        else:
            workflow_thread = Thread(target=run_workflow, daemon=True)
        workflow_thread.start()

        # Stream events
        if streaming_available:
            try:
                async for sse_data in stream_manager.stream_events():
                    yield sse_data
            except Exception as e:
                logger.error(f"Stream error: {e}")

        # Wait for workflow to complete
        workflow_thread.join(timeout=300)  # Longer timeout for planning mode (up to 10 rounds)

        # Handle planning session result
        if workflow_result.get("planning_session"):
            session = workflow_result["planning_session"]

            # Format planning result as a readable message
            response_text = _format_planning_result(session)

            # Build metadata for planning session
            full_metadata = {
                "planning_mode": True,
                "session_id": session.session_id,
                "status": session.status,
                "total_rounds": len(session.rounds),
                "agents_used": ["academic_planning", "programs_requirements", "course_scheduling", "policy_compliance"],
                "final_plan": session.final_plan.to_dict() if session.final_plan else None,
            }

            # Save planning result to database
            await add_message(conversation_id, "assistant", response_text, metadata=full_metadata)

            # Also save planning session to planning_sessions collection
            db = await MongoDB.get_db()
            await db.planning_sessions.insert_one({
                "session_id": session.session_id,
                "user_id": str(user["_id"]),
                "conversation_id": conversation_id,
                "request": data.message,
                "result": session.to_dict(),
                "status": session.status,
                "total_rounds": len(session.rounds),
                "created_at": datetime.utcnow()
            })

            # Send planning complete event with full session data
            yield f"data: {json.dumps({'type': 'planning_complete', 'data': {'session_id': session.session_id, 'status': session.status, 'total_rounds': len(session.rounds), 'final_plan': session.final_plan.to_dict() if session.final_plan else None}})}\n\n"

            # Send answer
            yield f"data: {json.dumps({'type': 'answer', 'data': {'content': response_text, 'conversation_id': conversation_id, 'agents_used': full_metadata['agents_used'], 'planning_mode': True, 'session_id': session.session_id}})}\n\n"

        # Send final answer for regular workflow
        elif workflow_result["result"]:
            result = workflow_result["result"]
            response_text = ""
            if result.get("messages"):
                last_msg = result["messages"][-1]
                response_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

            # Extract agent outputs for frontend display
            agents_used = list(result.get("agent_outputs", {}).keys())
            agent_details = {}
            for agent_name, output in result.get("agent_outputs", {}).items():
                agent_details[agent_name] = {
                    "answer": output.answer if hasattr(output, "answer") else str(output),
                    "confidence": output.confidence if hasattr(output, "confidence") else 0,
                    "risks": [{"type": r.type, "severity": r.severity, "description": r.description}
                              for r in (output.risks if hasattr(output, "risks") else [])],
                    "relevant_policies": output.relevant_policies if hasattr(output, "relevant_policies") else []
                }

            # Extract execution stats
            exec_meta = result.get("execution_metadata", {})
            phase_timing = result.get("phase_timing", {})

            # Build comprehensive metadata for MongoDB (restore full detail)
            full_metadata = {
                "system": data.system,  # which baseline/experiment was used
                "agents_used": agents_used,
                "agent_outputs": agent_details,
                "workflow_step": result.get("workflow_step", "WorkflowStep.COMPLETE"),
                "iteration_count": result.get("iteration_count", 0),
                "active_agents": result.get("active_agents", agents_used),
                "user_goal": result.get("user_goal", ""),
                "conflicts": [{"type": c.type, "description": c.description, "agents": c.agents_involved}
                              for c in result.get("conflicts", []) if hasattr(c, "type")],
                "risks": [{"type": r.type, "severity": r.severity, "description": r.description}
                          for r in result.get("risks", []) if hasattr(r, "type")],
                "execution_metadata": exec_meta,
                "phase_timing": phase_timing,
            }

            # Save to database with full metadata
            await add_message(conversation_id, "assistant", response_text, metadata=full_metadata)

            # Send comprehensive answer with workflow details
            yield f"data: {json.dumps({'type': 'answer', 'data': {'content': response_text, 'conversation_id': conversation_id, 'agents_used': agents_used, 'agent_details': agent_details, 'execution_stats': exec_meta, 'phase_timing': phase_timing}})}\n\n"

        elif workflow_result["error"]:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': workflow_result['error']}})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'data': {}})}\n\n"

        # Cleanup
        if streaming_available:
            set_stream_manager(None)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# =============================================================================
# Collaborative Planning Mode
# =============================================================================

# Import planning coordinator and agents
try:
    from planning.coordinator import PlanningModeCoordinator
    from agents.planning_agent import AcademicPlanningAgent
    from agents.programs_agent import ProgramsRequirementsAgent
    from agents.courses_agent import CourseSchedulingAgent
    from agents.policy_agent import PolicyComplianceAgent
    planning_available = True
except ImportError as e:
    logger.warning(f"Planning module not available: {e}")
    planning_available = False

# Cached agent instances for planning mode
_planning_agents = None

def get_planning_agents():
    """Get or create cached agent instances for planning mode."""
    global _planning_agents
    if _planning_agents is None:
        _planning_agents = {
            "planning": AcademicPlanningAgent(),
            "programs": ProgramsRequirementsAgent(),
            "courses": CourseSchedulingAgent(),
            "policy": PolicyComplianceAgent()
        }
    return _planning_agents


@app.post("/api/planning/start")
async def start_planning_session(
    request: PlanningRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a collaborative planning session with SSE streaming.

    The planning coordinator will:
    1. Have the Planning Agent propose an initial plan
    2. Run Programs, Courses, and Policy agents in PARALLEL
    3. Iterate up to 5 rounds until consensus or max rounds reached
    4. Stream real-time updates via SSE
    """
    if not planning_available:
        raise HTTPException(
            status_code=503,
            detail="Planning module not available"
        )

    user_id = str(current_user["_id"])
    conversation_id = request.conversation_id or f"conv_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    # Get user profile for context
    user_profile = current_user.get("profile", {})
    user_profile["_id"] = user_id

    # Event queue for SSE streaming
    event_queue = asyncio.Queue()

    def emit_event(event: dict):
        """Callback to emit events to the queue."""
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                event_queue.put_nowait, event
            )
        except Exception as e:
            logger.warning(f"Failed to emit event: {e}")

    async def generate_planning_stream():
        """Generator for SSE streaming of planning session."""
        try:
            # Get cached agents
            agents = get_planning_agents()

            # Create coordinator with event callback
            coordinator = PlanningModeCoordinator(
                planning_agent=agents["planning"],
                programs_agent=agents["programs"],
                courses_agent=agents["courses"],
                policy_agent=agents["policy"],
                emit_event=emit_event,
                db=None  # We'll handle DB separately
            )

            # Start planning in background task
            async def run_planning():
                return await coordinator.execute_planning_session(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    request=request.request,
                    student_profile=user_profile
                )

            planning_task = asyncio.create_task(run_planning())

            # Stream events as they come
            session_result = None
            while True:
                try:
                    # Wait for event with timeout
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.5)
                    yield f"data: {json.dumps({'type': event.get('type', 'update'), 'data': event})}\n\n"

                    # Check if planning is complete
                    if event.get("type") == "planning_complete":
                        break

                except asyncio.TimeoutError:
                    # Check if planning task is done
                    if planning_task.done():
                        session_result = planning_task.result()
                        break

            # Ensure we have the result
            if session_result is None:
                session_result = await planning_task

            # Save to MongoDB
            db = await MongoDB.get_db()
            await db.planning_sessions.insert_one({
                "session_id": session_result.session_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "request": request.request,
                "result": session_result.to_dict(),
                "status": session_result.status,
                "total_rounds": len(session_result.rounds),
                "created_at": datetime.utcnow()
            })

            yield f"data: {json.dumps({'type': 'done', 'data': {'session_id': session_result.session_id}})}\n\n"

        except Exception as e:
            logger.error(f"Planning session error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

    return StreamingResponse(
        generate_planning_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/planning/{session_id}")
async def get_planning_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get details of a specific planning session."""
    db = await MongoDB.get_db()
    session = await db.planning_sessions.find_one({
        "session_id": session_id,
        "user_id": current_user["_id"]
    })

    if not session:
        raise HTTPException(status_code=404, detail="Planning session not found")

    # Convert ObjectId to string for JSON serialization
    session["_id"] = str(session["_id"])
    return session


@app.get("/api/planning/user/history")
async def get_planning_history(
    current_user: dict = Depends(get_current_user),
    limit: int = 10
):
    """Get user's planning session history."""
    db = await MongoDB.get_db()
    cursor = db.planning_sessions.find(
        {"user_id": current_user["_id"]}
    ).sort("created_at", -1).limit(limit)

    sessions = []
    async for session in cursor:
        session["_id"] = str(session["_id"])
        sessions.append({
            "session_id": session["session_id"],
            "request": session["request"],
            "status": session.get("result", {}).get("status", "unknown"),
            "total_rounds": session.get("result", {}).get("total_rounds", 0),
            "created_at": session["created_at"].isoformat() if session.get("created_at") else None
        })

    return {"sessions": sessions}


@app.post("/api/planning/{session_id}/approve")
async def approve_planning_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Approve and save the final plan from a planning session."""
    db = await MongoDB.get_db()

    # Find the session
    session = await db.planning_sessions.find_one({
        "session_id": session_id,
        "user_id": current_user["_id"]
    })

    if not session:
        raise HTTPException(status_code=404, detail="Planning session not found")

    final_plan = session.get("result", {}).get("final_plan")
    if not final_plan:
        raise HTTPException(status_code=400, detail="No final plan available to approve")

    # Update session status to approved
    await db.planning_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"approved": True, "approved_at": datetime.utcnow()}}
    )

    # Save approved plan to user's profile or separate collection
    await db.approved_plans.insert_one({
        "user_id": current_user["_id"],
        "session_id": session_id,
        "plan": final_plan,
        "approved_at": datetime.utcnow()
    })

    return {"status": "approved", "session_id": session_id, "plan": final_plan}


# =============================================================================
# System Registry — Ablation Study
# =============================================================================

@app.get("/api/systems")
async def list_systems():
    """
    List available system configurations for the ablation study.

    The frontend uses this to populate the system-selector dropdown.
    Each system sends its ID in the `system` field of POST /api/chat.

    Ablation map
    ------------
    multi_agent vs multi_agent_opaque  → value of transparency
    multi_agent_opaque vs one_shot     → value of iterative evaluation
    one_shot vs single_agent           → value of agent specialisation
    single_agent vs single_agent_cot   → value of CoT within one call
    """
    return {
        "available": BASELINES_AVAILABLE,
        "default": "multi_agent",
        "systems": [
            {
                "id": "multi_agent",
                "name": "Full Multi-Agent (Transparent)",
                "description": (
                    "LLM routing → 4 parallel agents → coordinator evaluation "
                    "(up to 3 rounds) → LLM synthesis. Agent reasoning visible "
                    "in real time via streaming panel."
                ),
                "streaming": True,
                "ablation_variable": "experiment (full system)",
            },
            {
                "id": "multi_agent_opaque",
                "name": "Full Multi-Agent (Opaque)",
                "description": (
                    "Identical processing to multi_agent — same routing, same "
                    "agents, same evaluation loop, same synthesis — but streaming "
                    "events are suppressed. User sees only the final answer."
                ),
                "streaming": False,
                "ablation_variable": "removes: transparency / user visibility",
            },
            {
                "id": "one_shot",
                "name": "One-Shot Multi-Agent",
                "description": (
                    "LLM routing → 4 parallel agents → LLM synthesis. "
                    "The coordinator evaluation loop is skipped entirely "
                    "(no re-runs, no enhanced k=10 retrieval)."
                ),
                "streaming": False,
                "ablation_variable": "removes: iterative coordinator evaluation",
            },
            {
                "id": "single_agent",
                "name": "Baseline A — Single Agent",
                "description": (
                    "One GPT-5.2 call. All 5 RAG domains concatenated into "
                    "a single prompt. No coordinator, no specialisation. "
                    "Same model and same data as the full system."
                ),
                "streaming": False,
                "ablation_variable": "removes: multi-agent specialisation",
            },
            {
                "id": "single_agent_cot",
                "name": "Baseline B — Single Agent + CoT",
                "description": (
                    "Same as single_agent with explicit chain-of-thought "
                    "instructions injected before the answer."
                ),
                "streaming": False,
                "ablation_variable": "removes: specialisation; adds: CoT reasoning",
            },
        ],
    }


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

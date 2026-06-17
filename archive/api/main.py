"""
FastAPI Application - Multi-Agent Academic Advising System API
ACL 2026 Demo Track

This API provides:
- User authentication and management
- Student profile management with academic history
- Conversation history and session management
- Multi-agent advising chat interface
- Real-time streaming responses
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import logging
import time

from api.database import MongoDB
from api.routes import (
    auth_router,
    chat_router,
    users_router,
    profiles_router,
    conversations_router,
    health_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Multi-Agent Advising API...")

    # Connect to MongoDB
    try:
        await MongoDB.connect()
        logger.info("MongoDB connection established")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down API...")
    await MongoDB.disconnect()
    logger.info("MongoDB connection closed")


# Create FastAPI application
app = FastAPI(
    title="Multi-Agent Academic Advising API",
    description="""
    ## ACL 2026 Demo Track Submission

    A dynamic multi-agent system for academic advising that features:

    - **Orchestrated Collaboration**: Multiple specialized agents work together
    - **Visible Negotiation**: Transparent conflict resolution between agents
    - **Personalized Advising**: Uses student academic history for recommendations
    - **Interactive Workflow**: Real-time updates on agent activity

    ### Agents

    | Agent | Responsibility |
    |-------|----------------|
    | Programs & Requirements | Validates degree progress, proposes plans |
    | Course & Scheduling | Finds courses, checks conflicts |
    | Policy & Compliance | Enforces university policies |
    | Academic Planning | Creates multi-semester plans |

    ### Key Features

    - **Proposal + Critique Protocol**: Agents propose and critique each other's suggestions
    - **Blackboard Architecture**: Structured shared state for agent communication
    - **Conflict Detection**: Automatic identification of policy violations and trade-offs
    - **User Agency**: Interactive resolution of conflicts and decisions

    ### Authentication

    Use the `/auth/register` endpoint to create an account, then `/auth/login` to get a JWT token.
    Include the token in the `Authorization` header as `Bearer <token>`.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add X-Process-Time header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal error occurred",
            "type": type(exc).__name__
        }
    )


# Include routers
API_PREFIX = "/api/v1"

app.include_router(health_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(profiles_router, prefix=API_PREFIX)
app.include_router(conversations_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)


# Root endpoint
@app.get("/")
async def root():
    """API root - returns basic info."""
    return {
        "name": "Multi-Agent Academic Advising API",
        "version": "1.0.0",
        "description": "ACL 2026 Demo Track - Dynamic Multi-Agent System for Academic Advising",
        "docs": "/docs",
        "health": f"{API_PREFIX}/health"
    }


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Multi-Agent Academic Advising API",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    # Apply security globally
    openapi_schema["security"] = [{"bearerAuth": []}]

    # Add tags
    openapi_schema["tags"] = [
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "Authentication", "description": "User registration and login"},
        {"name": "Users", "description": "User management"},
        {"name": "Student Profiles", "description": "Academic profile management"},
        {"name": "Conversations", "description": "Chat history management"},
        {"name": "Chat", "description": "Multi-agent advising interface"}
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Entry point for uvicorn
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

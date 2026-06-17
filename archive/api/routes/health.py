"""
Health check endpoints for monitoring.
"""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any

from api.database import get_database


router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    components: Dict[str, Any]


@router.get("", response_model=HealthResponse)
async def health_check(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Check system health including database connectivity.
    """
    components = {}

    # Check MongoDB
    try:
        await db.command("ping")
        components["mongodb"] = {"status": "healthy"}
    except Exception as e:
        components["mongodb"] = {"status": "unhealthy", "error": str(e)}

    # Overall status
    all_healthy = all(
        c.get("status") == "healthy" for c in components.values()
    )

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        components=components
    )


@router.get("/ready")
async def readiness_check(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Kubernetes-style readiness probe.
    """
    try:
        await db.command("ping")
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    """
    return {"status": "alive"}

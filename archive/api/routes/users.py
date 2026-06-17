"""
User management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional

from api.database import get_database
from api.models.user import User, UserUpdate
from api.services.user_service import UserService
from api.routes.auth import get_current_user, require_role


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[User])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    role: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(require_role(["admin", "advisor"]))
):
    """
    List all users (admin/advisor only).
    """
    user_service = UserService(db)
    return await user_service.list_users(skip=skip, limit=limit, role=role)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific user's info.
    Students can only view their own info.
    """
    # Students can only view themselves
    if current_user.role == "student" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view other users"
        )

    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Update user info.
    Students can only update their own info (limited fields).
    """
    # Students can only update themselves
    if current_user.role == "student" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update other users"
        )

    # Students cannot change their role
    if current_user.role == "student" and update_data.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students cannot change their role"
        )

    user_service = UserService(db)
    user = await user_service.update_user(user_id, update_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Delete (deactivate) a user (admin only).
    """
    user_service = UserService(db)
    success = await user_service.delete_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

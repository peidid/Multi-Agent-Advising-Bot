"""
Student profile endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from api.database import get_database
from api.models.user import User
from api.models.student_profile import (
    StudentProfile, StudentProfileCreate, StudentProfileUpdate,
    StudentProfileSummary, CompletedCourse, CurrentEnrollment,
    DegreeProgress
)
from api.services.profile_service import ProfileService
from api.routes.auth import get_current_user, require_role


router = APIRouter(prefix="/profiles", tags=["Student Profiles"])


@router.post("", response_model=StudentProfile, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: StudentProfileCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Create a student profile.
    Students can only create their own profile.
    """
    # Students can only create their own profile
    if current_user.role == "student" and profile_data.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create profile for another user"
        )

    profile_service = ProfileService(db)

    try:
        profile = await profile_service.create_profile(profile_data)
        return profile
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me", response_model=StudentProfile)
async def get_my_profile(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's profile.
    """
    profile_service = ProfileService(db)
    profile = await profile_service.get_profile_by_user_id(current_user.id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create one first."
        )

    return profile


@router.get("/me/summary", response_model=StudentProfileSummary)
async def get_my_profile_summary(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Get lightweight summary of current user's profile.
    Used by agents for quick context.
    """
    profile_service = ProfileService(db)
    summary = await profile_service.get_profile_summary(current_user.id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return summary


@router.get("/{user_id}", response_model=StudentProfile)
async def get_profile(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Get a student's profile.
    Students can only view their own profile.
    """
    # Students can only view their own profile
    if current_user.role == "student" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view other profiles"
        )

    profile_service = ProfileService(db)
    profile = await profile_service.get_profile_by_user_id(user_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return profile


@router.put("/me", response_model=StudentProfile)
async def update_my_profile(
    update_data: StudentProfileUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Update the current user's profile.
    """
    profile_service = ProfileService(db)
    profile = await profile_service.update_profile(current_user.id, update_data)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return profile


@router.post("/me/courses/completed", response_model=StudentProfile)
async def add_completed_course(
    course: CompletedCourse,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Add a completed course to the profile.
    """
    profile_service = ProfileService(db)
    profile = await profile_service.add_completed_course(current_user.id, course)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return profile


@router.put("/me/courses/current", response_model=StudentProfile)
async def update_current_enrollment(
    courses: List[CurrentEnrollment],
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Update current semester enrollment.
    """
    profile_service = ProfileService(db)
    profile = await profile_service.update_current_enrollment(current_user.id, courses)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return profile


@router.get("/me/progress", response_model=List[DegreeProgress])
async def get_degree_progress(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate and get degree progress.
    """
    profile_service = ProfileService(db)
    progress = await profile_service.calculate_degree_progress(current_user.id)

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return progress


@router.post("/{user_id}/notes", response_model=StudentProfile)
async def add_advisor_note(
    user_id: str,
    note: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(require_role(["advisor", "admin"]))
):
    """
    Add an advisor note to a student's profile (advisors only).
    """
    profile_service = ProfileService(db)
    profile = await profile_service.add_advisor_note(
        user_id, note, current_user.id
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return profile


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_profile(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Delete the current user's profile.
    """
    profile_service = ProfileService(db)
    success = await profile_service.delete_profile(current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

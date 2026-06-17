"""
Conversation history endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional

from api.database import get_database
from api.models.user import User
from api.models.conversation import (
    Conversation, ConversationCreate, ConversationSummary, Message
)
from api.services.conversation_service import ConversationService
from api.routes.auth import get_current_user


router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: Optional[ConversationCreate] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new conversation.
    """
    conv_service = ConversationService(db)

    initial_message = data.initial_message if data else None
    conversation = await conv_service.create_conversation(
        user_id=current_user.id,
        initial_message=initial_message
    )

    return conversation


@router.get("", response_model=List[ConversationSummary])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = False,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    List user's conversations.
    """
    conv_service = ConversationService(db)

    return await conv_service.list_conversations(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        active_only=active_only
    )


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific conversation.
    """
    conv_service = ConversationService(db)
    conversation = await conv_service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Check ownership
    if conversation.user_id != current_user.id and current_user.role not in ["admin", "advisor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this conversation"
        )

    return conversation


@router.get("/{conversation_id}/messages", response_model=List[Message])
async def get_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Get messages from a conversation with pagination.
    """
    conv_service = ConversationService(db)

    # Verify ownership
    conversation = await conv_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id and current_user.role not in ["admin", "advisor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this conversation"
        )

    return await conv_service.get_messages(conversation_id, skip=skip, limit=limit)


@router.post("/{conversation_id}/close", response_model=dict)
async def close_conversation(
    conversation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Close/archive a conversation.
    """
    conv_service = ConversationService(db)

    # Verify ownership
    conversation = await conv_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to close this conversation"
        )

    success = await conv_service.close_conversation(conversation_id)

    return {"success": success, "message": "Conversation closed"}


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a conversation permanently.
    """
    conv_service = ConversationService(db)

    # Verify ownership
    conversation = await conv_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this conversation"
        )

    success = await conv_service.delete_conversation(conversation_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )

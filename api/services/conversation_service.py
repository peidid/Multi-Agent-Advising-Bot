"""
Conversation service for chat history management.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.models.conversation import (
    Conversation, ConversationCreate, ConversationSummary,
    Message, MessageRole, WorkflowState, WorkflowStep,
    AgentOutput, ConflictInfo
)
from api.database import CONVERSATIONS_COLLECTION


class ConversationService:
    """Service for conversation operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[CONVERSATIONS_COLLECTION]

    async def create_conversation(
        self,
        user_id: str,
        initial_message: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation."""
        conv_doc = {
            "user_id": user_id,
            "title": None,
            "is_active": True,
            "messages": [],
            "current_workflow": None,
            "student_profile_snapshot": None,
            "topics_discussed": [],
            "courses_mentioned": [],
            "decisions_made": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_message_at": None,
            "total_messages": 0,
            "total_agent_calls": 0,
            "total_conflicts_resolved": 0
        }

        # Add initial message if provided
        if initial_message:
            message = {
                "id": str(datetime.utcnow().timestamp()),
                "role": MessageRole.USER.value,
                "content": initial_message,
                "timestamp": datetime.utcnow(),
                "agent_name": None,
                "agent_output": None,
                "workflow_state": None,
                "metadata": {}
            }
            conv_doc["messages"].append(message)
            conv_doc["total_messages"] = 1
            conv_doc["last_message_at"] = datetime.utcnow()

            # Generate title from first message
            conv_doc["title"] = self._generate_title(initial_message)

        result = await self.collection.insert_one(conv_doc)
        conv_doc["_id"] = str(result.inserted_id)

        return self._doc_to_conversation(conv_doc)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        if not ObjectId.is_valid(conversation_id):
            return None

        conv_doc = await self.collection.find_one({"_id": ObjectId(conversation_id)})
        if not conv_doc:
            return None

        return self._doc_to_conversation(conv_doc)

    async def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        agent_name: Optional[str] = None,
        agent_output: Optional[AgentOutput] = None,
        workflow_state: Optional[WorkflowState] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """Add a message to a conversation."""
        if not ObjectId.is_valid(conversation_id):
            return None

        message_doc = {
            "id": str(datetime.utcnow().timestamp()),
            "role": role.value,
            "content": content,
            "timestamp": datetime.utcnow(),
            "agent_name": agent_name,
            "agent_output": agent_output.model_dump() if agent_output else None,
            "workflow_state": workflow_state.model_dump() if workflow_state else None,
            "metadata": metadata or {}
        }

        # Update conversation
        update_doc = {
            "$push": {"messages": message_doc},
            "$set": {
                "updated_at": datetime.utcnow(),
                "last_message_at": datetime.utcnow()
            },
            "$inc": {"total_messages": 1}
        }

        # Increment agent calls if this is an agent message
        if role == MessageRole.AGENT:
            update_doc["$inc"]["total_agent_calls"] = 1

        result = await self.collection.update_one(
            {"_id": ObjectId(conversation_id)},
            update_doc
        )

        if result.modified_count == 0:
            return None

        return Message(
            id=message_doc["id"],
            role=role,
            content=content,
            timestamp=message_doc["timestamp"],
            agent_name=agent_name,
            agent_output=agent_output,
            workflow_state=workflow_state,
            metadata=metadata or {}
        )

    async def update_workflow_state(
        self,
        conversation_id: str,
        workflow_state: WorkflowState
    ) -> bool:
        """Update the current workflow state."""
        if not ObjectId.is_valid(conversation_id):
            return False

        result = await self.collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$set": {
                    "current_workflow": workflow_state.model_dump(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    async def add_conflict_resolved(self, conversation_id: str) -> bool:
        """Increment conflicts resolved counter."""
        if not ObjectId.is_valid(conversation_id):
            return False

        result = await self.collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$inc": {"total_conflicts_resolved": 1}}
        )

        return result.modified_count > 0

    async def add_topic(self, conversation_id: str, topic: str) -> bool:
        """Add a discussed topic."""
        if not ObjectId.is_valid(conversation_id):
            return False

        result = await self.collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$addToSet": {"topics_discussed": topic}}
        )

        return result.modified_count > 0

    async def add_course_mention(self, conversation_id: str, course_code: str) -> bool:
        """Add a mentioned course."""
        if not ObjectId.is_valid(conversation_id):
            return False

        result = await self.collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$addToSet": {"courses_mentioned": course_code}}
        )

        return result.modified_count > 0

    async def add_decision(
        self,
        conversation_id: str,
        decision: Dict[str, Any]
    ) -> bool:
        """Record a decision made in conversation."""
        if not ObjectId.is_valid(conversation_id):
            return False

        decision["timestamp"] = datetime.utcnow()

        result = await self.collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$push": {"decisions_made": decision},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        return result.modified_count > 0

    async def set_profile_snapshot(
        self,
        conversation_id: str,
        profile_snapshot: Dict[str, Any]
    ) -> bool:
        """Set the student profile snapshot for context."""
        if not ObjectId.is_valid(conversation_id):
            return False

        result = await self.collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": {"student_profile_snapshot": profile_snapshot}}
        )

        return result.modified_count > 0

    async def list_conversations(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        active_only: bool = False
    ) -> List[ConversationSummary]:
        """List conversations for a user."""
        query = {"user_id": user_id}
        if active_only:
            query["is_active"] = True

        cursor = self.collection.find(query).sort(
            "last_message_at", -1
        ).skip(skip).limit(limit)

        summaries = []
        async for conv_doc in cursor:
            # Get preview from last message
            preview = None
            if conv_doc.get("messages"):
                last_msg = conv_doc["messages"][-1]
                preview = last_msg["content"][:100] + "..." if len(last_msg["content"]) > 100 else last_msg["content"]

            summaries.append(ConversationSummary(
                id=str(conv_doc["_id"]),
                user_id=conv_doc["user_id"],
                title=conv_doc.get("title"),
                created_at=conv_doc["created_at"],
                last_message_at=conv_doc.get("last_message_at"),
                total_messages=conv_doc.get("total_messages", 0),
                is_active=conv_doc.get("is_active", True),
                preview=preview
            ))

        return summaries

    async def close_conversation(self, conversation_id: str) -> bool:
        """Mark conversation as inactive."""
        if not ObjectId.is_valid(conversation_id):
            return False

        result = await self.collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        if not ObjectId.is_valid(conversation_id):
            return False

        result = await self.collection.delete_one({"_id": ObjectId(conversation_id)})
        return result.deleted_count > 0

    async def get_messages(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Message]:
        """Get messages from a conversation with pagination."""
        if not ObjectId.is_valid(conversation_id):
            return []

        conv_doc = await self.collection.find_one(
            {"_id": ObjectId(conversation_id)},
            {"messages": {"$slice": [skip, limit]}}
        )

        if not conv_doc or not conv_doc.get("messages"):
            return []

        return [self._doc_to_message(m) for m in conv_doc["messages"]]

    def _generate_title(self, first_message: str) -> str:
        """Generate a title from the first message."""
        # Take first 50 chars and clean up
        title = first_message[:50].strip()
        if len(first_message) > 50:
            title += "..."
        return title

    def _doc_to_conversation(self, doc: Dict[str, Any]) -> Conversation:
        """Convert MongoDB document to Conversation model."""
        return Conversation(
            _id=str(doc["_id"]),
            user_id=doc["user_id"],
            title=doc.get("title"),
            is_active=doc.get("is_active", True),
            messages=[self._doc_to_message(m) for m in doc.get("messages", [])],
            current_workflow=WorkflowState(**doc["current_workflow"]) if doc.get("current_workflow") else None,
            student_profile_snapshot=doc.get("student_profile_snapshot"),
            topics_discussed=doc.get("topics_discussed", []),
            courses_mentioned=doc.get("courses_mentioned", []),
            decisions_made=doc.get("decisions_made", []),
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow()),
            last_message_at=doc.get("last_message_at"),
            total_messages=doc.get("total_messages", 0),
            total_agent_calls=doc.get("total_agent_calls", 0),
            total_conflicts_resolved=doc.get("total_conflicts_resolved", 0)
        )

    def _doc_to_message(self, doc: Dict[str, Any]) -> Message:
        """Convert message document to Message model."""
        return Message(
            id=doc.get("id", ""),
            role=MessageRole(doc["role"]),
            content=doc["content"],
            timestamp=doc.get("timestamp", datetime.utcnow()),
            agent_name=doc.get("agent_name"),
            agent_output=AgentOutput(**doc["agent_output"]) if doc.get("agent_output") else None,
            workflow_state=WorkflowState(**doc["workflow_state"]) if doc.get("workflow_state") else None,
            metadata=doc.get("metadata", {})
        )

"""
Chat endpoints - Main advising interface.
Integrates with the multi-agent workflow.
Supports real-time streaming for Claude/Gemini-style visibility.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, AsyncGenerator
from datetime import datetime
import json
import asyncio
import time
from threading import Thread

from api.database import get_database
from api.models.user import User
from api.models.conversation import (
    ChatRequest, ChatResponse, Message, MessageRole,
    WorkflowState, WorkflowStep, AgentOutput, AgentStatus,
    StreamingChunk
)
from api.models.student_profile import StudentProfileSummary
from api.services.conversation_service import ConversationService
from api.services.profile_service import ProfileService
from api.routes.auth import get_current_user, get_current_user_optional

# Import streaming infrastructure
try:
    from streaming.callback import StreamCallbackManager, set_stream_manager
    from streaming.events import workflow_start_event
    STREAMING_AVAILABLE = True
except ImportError:
    STREAMING_AVAILABLE = False
    StreamCallbackManager = None


router = APIRouter(prefix="/chat", tags=["Chat"])


class MultiAgentRunner:
    """
    Async wrapper for the multi-agent workflow.
    Allows running the LangGraph workflow in async context.
    """

    def __init__(self):
        # Import here to avoid circular imports and initialization on module load
        self._app = None
        self._coordinator = None

    def _get_app(self):
        """Lazy load the LangGraph app."""
        if self._app is None:
            # Import the compiled workflow
            from multi_agent import app, coordinator
            self._app = app
            self._coordinator = coordinator
        return self._app, self._coordinator

    async def run(
        self,
        user_query: str,
        student_profile: Optional[dict] = None,
        conversation_history: Optional[list] = None
    ) -> dict:
        """
        Run the multi-agent workflow.

        Args:
            user_query: The user's question
            student_profile: Student profile summary for personalization
            conversation_history: Previous messages for context

        Returns:
            The final state from the workflow
        """
        from langchain_core.messages import HumanMessage, AIMessage
        from blackboard.schema import WorkflowStep

        app, _ = self._get_app()

        # Build message history
        messages = []
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg.get("role") in ["assistant", "agent"]:
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_query))

        # Build initial state
        initial_state = {
            "user_query": user_query,
            "student_profile": student_profile or {},
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

        # Run workflow in thread pool to not block
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, app.invoke, initial_state)

        return result

    async def run_streaming(
        self,
        user_query: str,
        student_profile: Optional[dict] = None,
        conversation_history: Optional[list] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Run the multi-agent workflow with streaming updates.

        Yields status updates as the workflow progresses.
        """
        from langchain_core.messages import HumanMessage, AIMessage
        from blackboard.schema import WorkflowStep

        app, coordinator = self._get_app()

        # Build message history
        messages = []
        if conversation_history:
            for msg in conversation_history[-10:]:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg.get("role") in ["assistant", "agent"]:
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_query))

        initial_state = {
            "user_query": user_query,
            "student_profile": student_profile or {},
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

        # Yield initial status
        yield {
            "type": "status",
            "data": {"step": "starting", "message": "Analyzing your question..."}
        }

        # Stream through the workflow using LangGraph's stream method
        loop = asyncio.get_event_loop()

        def run_stream():
            results = []
            for chunk in app.stream(initial_state):
                results.append(chunk)
            return results

        chunks = await loop.run_in_executor(None, run_stream)

        for chunk in chunks:
            # Parse chunk and yield appropriate updates
            for node_name, node_output in chunk.items():
                if node_name == "coordinator":
                    workflow_step = node_output.get("workflow_step")
                    if workflow_step:
                        yield {
                            "type": "status",
                            "data": {
                                "step": workflow_step.value if hasattr(workflow_step, 'value') else str(workflow_step),
                                "active_agents": node_output.get("active_agents", [])
                            }
                        }

                elif node_name in ["programs", "courses", "policy", "planning"]:
                    agent_outputs = node_output.get("agent_outputs", {})
                    for agent_name, output in agent_outputs.items():
                        yield {
                            "type": "agent_complete",
                            "data": {
                                "agent": agent_name,
                                "confidence": output.confidence if hasattr(output, 'confidence') else 0,
                                "has_risks": len(output.risks) > 0 if hasattr(output, 'risks') else False
                            }
                        }

                elif node_name == "synthesize":
                    # Final answer
                    messages = node_output.get("messages", [])
                    if messages:
                        final_answer = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
                        yield {
                            "type": "content",
                            "data": {"answer": final_answer}
                        }

        yield {"type": "done", "data": {}}


# Global runner instance
agent_runner = MultiAgentRunner()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message and get an AI-powered advising response.

    This endpoint:
    1. Creates or continues a conversation
    2. Retrieves the user's student profile for personalization
    3. Runs the multi-agent workflow
    4. Stores the conversation history
    5. Returns the response with workflow details
    """
    start_time = time.time()

    conv_service = ConversationService(db)
    profile_service = ProfileService(db)

    # Get or create conversation
    if request.conversation_id:
        conversation = await conv_service.get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )
    else:
        conversation = await conv_service.create_conversation(
            user_id=current_user.id,
            initial_message=request.message
        )

    # Add user message if not the initial message
    if request.conversation_id:
        await conv_service.add_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message
        )

    # Get student profile for personalization
    profile_summary = await profile_service.get_profile_summary(current_user.id)
    student_profile = None
    if profile_summary:
        student_profile = {
            "major": [profile_summary.primary_major] + profile_summary.additional_majors,
            "minors": profile_summary.minors,
            "gpa": profile_summary.current_gpa,
            "completed_courses": profile_summary.completed_course_codes,
            "current_courses": profile_summary.current_course_codes,
            "flags": profile_summary.flags,
            "academic_standing": profile_summary.academic_standing.value
        }

        # Set profile snapshot if this is a new conversation
        if not request.conversation_id:
            await conv_service.set_profile_snapshot(
                conversation.id,
                student_profile
            )

    # Build conversation history for context
    conv_history = []
    if conversation.messages:
        for msg in conversation.messages:
            conv_history.append({
                "role": msg.role.value,
                "content": msg.content
            })

    # Run multi-agent workflow
    try:
        result = await agent_runner.run(
            user_query=request.message,
            student_profile=student_profile,
            conversation_history=conv_history
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )

    # Extract final answer
    final_answer = ""
    if result.get("messages"):
        last_message = result["messages"][-1]
        final_answer = last_message.content if hasattr(last_message, 'content') else str(last_message)

    # Build workflow state for response
    workflow_state = None
    if request.include_workflow_details:
        agent_outputs_dict = {}
        for agent_name, output in result.get("agent_outputs", {}).items():
            agent_outputs_dict[agent_name] = AgentOutput(
                agent_name=agent_name,
                agent_type=agent_name,
                answer=output.answer if hasattr(output, 'answer') else "",
                confidence=output.confidence if hasattr(output, 'confidence') else 0,
                relevant_policies=[p.policy_citation if hasattr(p, 'policy_citation') else str(p)
                                   for p in (output.relevant_policies if hasattr(output, 'relevant_policies') else [])],
                risks=[{"type": r.type, "severity": r.severity, "description": r.description}
                       for r in (output.risks if hasattr(output, 'risks') else [])],
                status=AgentStatus.COMPLETE
            )

        workflow_state = WorkflowState(
            step=WorkflowStep(result.get("workflow_step", "complete").value
                             if hasattr(result.get("workflow_step"), 'value')
                             else str(result.get("workflow_step", "complete"))),
            active_agents=result.get("active_agents", []),
            completed_agents=list(result.get("agent_outputs", {}).keys()),
            agent_outputs=agent_outputs_dict,
            conflicts=[],  # Would extract from result
            iteration_count=result.get("iteration_count", 0)
        )

    # Add assistant message to conversation
    assistant_message = await conv_service.add_message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=final_answer,
        workflow_state=workflow_state
    )

    # Extract sources and track courses mentioned
    sources = []
    for agent_name, output in result.get("agent_outputs", {}).items():
        if hasattr(output, 'sources'):
            sources.extend(output.sources)
        if hasattr(output, 'relevant_policies'):
            sources.extend([p.policy_citation if hasattr(p, 'policy_citation') else str(p)
                          for p in output.relevant_policies])

    # Calculate total time
    total_time_ms = int((time.time() - start_time) * 1000)

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id if assistant_message else "",
        response=final_answer,
        workflow=workflow_state,
        agents_used=list(result.get("agent_outputs", {}).keys()),
        conflicts_detected=len(result.get("conflicts", [])),
        sources=list(set(sources))[:10],  # Dedupe and limit
        total_time_ms=total_time_ms
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message and get a streaming response.

    This endpoint streams real-time updates as the multi-agent
    workflow progresses, allowing the UI to show agent activity.

    Uses Server-Sent Events (SSE) for real-time updates, similar to
    how Claude and Gemini show their thinking process.
    """
    conv_service = ConversationService(db)
    profile_service = ProfileService(db)

    # Get or create conversation
    if request.conversation_id:
        conversation = await conv_service.get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized"
            )
        conversation_id = conversation.id
    else:
        conversation = await conv_service.create_conversation(
            user_id=current_user.id,
            initial_message=request.message
        )
        conversation_id = conversation.id

    # Get profile
    profile_summary = await profile_service.get_profile_summary(current_user.id)
    student_profile = None
    if profile_summary:
        student_profile = {
            "major": [profile_summary.primary_major] + profile_summary.additional_majors,
            "gpa": profile_summary.current_gpa,
            "flags": profile_summary.flags
        }

    # Build history
    conv_history = []
    if conversation.messages:
        for msg in conversation.messages:
            conv_history.append({
                "role": msg.role.value,
                "content": msg.content
            })

    async def generate():
        """Generate SSE stream with real-time agent updates."""

        # Check if streaming infrastructure is available
        if not STREAMING_AVAILABLE:
            # Fallback to simple streaming
            try:
                async for chunk in agent_runner.run_streaming(
                    user_query=request.message,
                    student_profile=student_profile,
                    conversation_history=conv_history
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"
            return

        # Create stream manager for this request
        stream_manager = StreamCallbackManager()

        # Set as the global stream manager for this request
        set_stream_manager(stream_manager)

        # Emit workflow start event
        stream_manager.emit(workflow_start_event(request.message))
        yield stream_manager.get_callback()._events[-1].to_sse() if stream_manager.get_callback()._events else ""

        # Variables to capture the result
        workflow_result = {"result": None, "error": None}

        def run_workflow():
            """Run the workflow in a background thread."""
            try:
                from langchain_core.messages import HumanMessage, AIMessage
                from blackboard.schema import WorkflowStep as WFStep
                from multi_agent import app

                # Build message history
                messages = []
                if conv_history:
                    for msg in conv_history[-10:]:
                        if msg.get("role") == "user":
                            messages.append(HumanMessage(content=msg["content"]))
                        elif msg.get("role") in ["assistant", "agent"]:
                            messages.append(AIMessage(content=msg["content"]))

                messages.append(HumanMessage(content=request.message))

                initial_state = {
                    "user_query": request.message,
                    "student_profile": student_profile or {},
                    "agent_outputs": {},
                    "constraints": [],
                    "risks": [],
                    "plan_options": [],
                    "conflicts": [],
                    "open_questions": [],
                    "messages": messages,
                    "active_agents": [],
                    "workflow_step": WFStep.INITIAL,
                    "iteration_count": 0,
                    "next_agent": None,
                    "user_goal": None
                }

                result = app.invoke(initial_state)
                workflow_result["result"] = result

            except Exception as e:
                workflow_result["error"] = str(e)
            finally:
                stream_manager.mark_done()

        # Start workflow in background thread
        workflow_thread = Thread(target=run_workflow, daemon=True)
        workflow_thread.start()

        # Stream events as they arrive
        try:
            async for sse_data in stream_manager.stream_events():
                yield sse_data

            # After workflow completes, send final answer
            if workflow_result["result"]:
                result = workflow_result["result"]
                final_answer = ""
                if result.get("messages"):
                    last_message = result["messages"][-1]
                    final_answer = last_message.content if hasattr(last_message, 'content') else str(last_message)

                # Send the final answer
                yield f"data: {json.dumps({'type': 'answer', 'data': {'content': final_answer, 'conversation_id': conversation_id}})}\n\n"

                # Store the answer in conversation (async operation)
                # Note: We can't await here directly, so we'll do it after the generator
                asyncio.create_task(
                    conv_service.add_message(
                        conversation_id=conversation_id,
                        role=MessageRole.ASSISTANT,
                        content=final_answer
                    )
                )

            elif workflow_result["error"]:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': workflow_result['error']}})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'data': {}})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"
        finally:
            # Clean up
            set_stream_manager(None)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/quick")
async def quick_chat(
    request: ChatRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Quick chat without authentication (for demos).

    Uses a temporary conversation and no personalization.
    Limited to simple queries.
    """
    # Run workflow without personalization
    try:
        result = await agent_runner.run(
            user_query=request.message,
            student_profile=None,
            conversation_history=None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )

    # Extract answer
    final_answer = ""
    if result.get("messages"):
        last_message = result["messages"][-1]
        final_answer = last_message.content if hasattr(last_message, 'content') else str(last_message)

    return {
        "response": final_answer,
        "agents_used": list(result.get("agent_outputs", {}).keys())
    }

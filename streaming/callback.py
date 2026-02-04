"""
Callback system for streaming events.
Allows agents and coordinator to emit events that are streamed to the frontend.
"""
from typing import Callable, Optional, List
from queue import Queue
from threading import Lock
import asyncio

from .events import StreamEvent, EventType


class StreamCallback:
    """
    Callback interface for streaming events.

    Agents and the coordinator use this to emit events during execution.
    The events are collected and streamed to the frontend via SSE.
    """

    def __init__(self, queue: Optional[Queue] = None):
        """
        Initialize callback.

        Args:
            queue: Thread-safe queue to put events into.
                   If None, events are collected internally.
        """
        self._queue = queue
        self._events: List[StreamEvent] = []
        self._lock = Lock()

    def emit(self, event: StreamEvent) -> None:
        """
        Emit a streaming event.

        Thread-safe - can be called from multiple agents running in parallel.
        """
        with self._lock:
            if self._queue is not None:
                self._queue.put(event)
            else:
                self._events.append(event)

    def get_events(self) -> List[StreamEvent]:
        """Get all collected events (if not using queue mode)."""
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        """Clear collected events."""
        with self._lock:
            self._events.clear()


class StreamCallbackManager:
    """
    Manages streaming callbacks across the workflow.

    Creates a shared queue that all components write to,
    and provides async iteration for SSE streaming.
    """

    def __init__(self):
        self._queue: Queue = Queue()
        self._callback = StreamCallback(self._queue)
        self._done = False
        self._lock = Lock()

    def get_callback(self) -> StreamCallback:
        """Get the callback for agents/coordinator to use."""
        return self._callback

    def emit(self, event: StreamEvent) -> None:
        """Convenience method to emit directly from manager."""
        self._callback.emit(event)

    def mark_done(self) -> None:
        """Signal that the workflow is complete."""
        with self._lock:
            self._done = True
        # Put a sentinel to unblock waiting consumers
        self._queue.put(None)

    def is_done(self) -> bool:
        """Check if workflow is complete."""
        with self._lock:
            return self._done

    async def stream_events(self):
        """
        Async generator that yields events as they arrive.

        Use this with FastAPI's StreamingResponse for SSE.
        """
        loop = asyncio.get_event_loop()

        while True:
            # Get from queue in a non-blocking way using run_in_executor
            try:
                event = await loop.run_in_executor(
                    None,
                    lambda: self._queue.get(timeout=0.1)
                )

                if event is None:
                    # Sentinel received - workflow done
                    break

                yield event.to_sse()

            except Exception:
                # Queue.get timeout - check if we should stop
                if self.is_done() and self._queue.empty():
                    break
                continue

    def get_pending_events(self) -> List[StreamEvent]:
        """Get all pending events without blocking."""
        events = []
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                if event is not None:
                    events.append(event)
            except:
                break
        return events


# Global callback manager for the current request
# In production, this would be request-scoped
_current_manager: Optional[StreamCallbackManager] = None


def get_stream_manager() -> Optional[StreamCallbackManager]:
    """Get the current stream manager."""
    global _current_manager
    return _current_manager


def set_stream_manager(manager: Optional[StreamCallbackManager]) -> None:
    """Set the current stream manager."""
    global _current_manager
    _current_manager = manager


def emit_event(event: StreamEvent) -> None:
    """
    Emit an event to the current stream manager if one exists.

    Safe to call even when not streaming - will be a no-op.
    """
    manager = get_stream_manager()
    if manager is not None:
        manager.emit(event)

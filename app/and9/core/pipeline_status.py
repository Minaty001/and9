"""
AND9 — Pipeline Status.
Tracks and broadcasts the real-time execution stage of the assistant.
"""
import time
import logging
from typing import Dict, Any, List, Callable

logger = logging.getLogger(__name__)

class PipelineStage:
    LISTENING = "LISTENING"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    RETRYING = "RETRYING"
    DEGRADED = "DEGRADED"

class PipelineStatusManager:
    """Manages the current stage of the assistant pipeline and notifies listeners."""
    
    def __init__(self):
        self._current_stage = PipelineStage.LISTENING
        self._stage_history = []
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._start_time = time.time()
        self._stage_start_time = time.time()
        
    def register_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self._listeners.append(callback)
        # Send current status immediately
        try:
            callback(self.get_status())
        except Exception as e:
            logger.warning(f"Error calling status listener on register: {e}")
        
    def unregister_listener(self, callback: Callable[[Dict[str, Any]], None]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def set_stage(self, stage: str, details: str = ""):
        """Update the current execution stage and notify listeners."""
        now = time.time()
        duration_ms = (now - self._stage_start_time) * 1000
        
        # Log transition
        logger.info(f"Pipeline Stage Transition: {self._current_stage} -> {stage} ({details})")
        
        self._current_stage = stage
        self._stage_start_time = now
        
        status = {
            "stage": stage,
            "details": details,
            "timestamp": now,
            "duration_ms": duration_ms,
            "total_elapsed_ms": (now - self._start_time) * 1000
        }
        
        self._stage_history.append(status)
        if len(self._stage_history) > 20:
            self._stage_history.pop(0)
            
        # Notify listeners
        for listener in self._listeners:
            try:
                listener(status)
            except Exception as e:
                logger.warning(f"Error calling status listener: {e}")

    def reset(self):
        """Reset the pipeline timing."""
        self._start_time = time.time()
        self._stage_start_time = time.time()
        self.set_stage(PipelineStage.LISTENING, "Started fresh request")

    def get_status(self) -> Dict[str, Any]:
        """Get the current pipeline status."""
        now = time.time()
        return {
            "stage": self._current_stage,
            "stage_duration_ms": (now - self._stage_start_time) * 1000,
            "total_elapsed_ms": (now - self._start_time) * 1000,
            "history": self._stage_history
        }

# Global Status Manager Singleton
status_manager = PipelineStatusManager()

"""
Phase 45 — Roadmap
===================

Implements the forward-looking roadmap for JARVIS including
multi-agent orchestration, multimodal processing, offline-first
caching, plugin marketplace, and autonomous workflows.

Components:
    - MultiAgentOrchestrator: Register, assign, and orchestrate agents
    - MultimodalProcessor: Process image, audio, video, and text inputs
    - OfflineManager: Cache data for offline-first operation
    - PluginMarketplace: Browse, install, and rate plugins
    - WorkflowEngine: Create and execute multi-step workflows
    - RoadmapService: ServiceBase wrapper
"""

from .multi_agent import MultiAgentOrchestrator
from .multimodal import MultimodalProcessor
from .offline import OfflineManager
from .marketplace import PluginMarketplace
from .workflows import WorkflowEngine
from .service import RoadmapService
from .config import RoadmapConfig
from .models import AgentSpec, AgentTask, MultimodalInput, PluginListing, Workflow, WorkflowStep

__all__ = [
    "MultiAgentOrchestrator",
    "MultimodalProcessor",
    "OfflineManager",
    "PluginMarketplace",
    "WorkflowEngine",
    "RoadmapService",
    "RoadmapConfig",
    "AgentSpec",
    "AgentTask",
    "MultimodalInput",
    "PluginListing",
    "Workflow",
    "WorkflowStep",
]

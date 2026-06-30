"""
Phase 44 — Continuous Improvement
===================================

Collects user feedback, runs benchmarks, refines prompts, and supports
A/B testing to drive continuous improvement of JARVIS.

Components:
    - FeedbackCollector: Collect, query, and analyze user feedback
    - BenchmarkEngine: Run and compare performance benchmarks
    - PromptRefiner: Manage prompt versions and refinements
    - ABTestRunner: Create and analyze A/B tests
    - ImprovementService: ServiceBase wrapper
"""

from .feedback import FeedbackCollector
from .benchmarking import BenchmarkEngine
from .prompt_refinement import PromptRefiner
from .ab_testing import ABTestRunner
from .service import ImprovementService
from .config import ImprovementConfig
from .models import Feedback, BenchmarkResult, PromptVersion, ABTest

__all__ = [
    "FeedbackCollector",
    "BenchmarkEngine",
    "PromptRefiner",
    "ABTestRunner",
    "ImprovementService",
    "ImprovementConfig",
    "Feedback",
    "BenchmarkResult",
    "PromptVersion",
    "ABTest",
]

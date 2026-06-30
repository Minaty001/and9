"""
Phase 44 — Improvement Service.

ServiceBase wrapper for the Continuous Improvement subsystem.
Provides feedback collection, benchmarking, prompt refinement, and A/B testing.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import ImprovementConfig
from .models import Feedback, BenchmarkResult, PromptVersion, ABTest
from .feedback import FeedbackCollector
from .benchmarking import BenchmarkEngine
from .prompt_refinement import PromptRefiner
from .ab_testing import ABTestRunner

logger = logging.getLogger(__name__)


class ImprovementService(ServiceBase):
    """Continuous improvement service.

    Usage:
        svc = ImprovementService()
        await svc.initialize()
        fb = await svc.submit_feedback("user1", 5, "usability", "Amazing!")
        result = await svc.run_benchmark("parse", lambda: None)
    """

    def __init__(self, config: Optional[ImprovementConfig] = None):
        super().__init__(name="jarvis_improvement", version="1.0.0")
        self.config = config or ImprovementConfig()
        self.feedback_collector: Optional[FeedbackCollector] = None
        self.benchmark_engine: Optional[BenchmarkEngine] = None
        self.prompt_refiner: Optional[PromptRefiner] = None
        self.ab_test_runner: Optional[ABTestRunner] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.feedback_collector = FeedbackCollector(self.config)
            self.benchmark_engine = BenchmarkEngine(self.config)
            self.prompt_refiner = PromptRefiner(self.config)
            if self.config.enable_a_b_testing:
                self.ab_test_runner = ABTestRunner(self.config)

            self._metrics.reset()
            self._initialized = True
            logger.info("ImprovementService initialized")
            return True
        except Exception as e:
            logger.error("ImprovementService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("ImprovementService shutting down...")
        self._initialized = False

    # ── Feedback ──────────────────────────────────────────────────

    async def submit_feedback(
        self,
        user_id: str,
        rating: int,
        category: str = "other",
        comment: str = "",
        session_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Feedback:
        if not self.feedback_collector:
            raise RuntimeError("ImprovementService not initialized")
        fb = self.feedback_collector.submit_feedback(user_id, rating, category, comment, session_id, metadata)
        self._metrics.counter("feedback_submitted", 1)
        return fb

    async def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        if not self.feedback_collector:
            raise RuntimeError("ImprovementService not initialized")
        return self.feedback_collector.get_feedback(feedback_id)

    async def list_feedback(
        self,
        category: Optional[str] = None,
        min_rating: Optional[int] = None,
    ) -> List[Feedback]:
        if not self.feedback_collector:
            raise RuntimeError("ImprovementService not initialized")
        return self.feedback_collector.list_feedback(category, min_rating)

    async def get_feedback_stats(self) -> Dict[str, Any]:
        if not self.feedback_collector:
            raise RuntimeError("ImprovementService not initialized")
        return self.feedback_collector.get_stats()

    async def export_feedback(self, fmt: str = "json") -> str:
        if not self.feedback_collector:
            raise RuntimeError("ImprovementService not initialized")
        return self.feedback_collector.export_feedback(fmt)

    # ── Benchmarking ──────────────────────────────────────────────

    async def run_benchmark(
        self,
        name: str,
        test_func: Callable[[], Any],
        iterations: int = 10,
    ) -> BenchmarkResult:
        if not self.benchmark_engine:
            raise RuntimeError("ImprovementService not initialized")
        t0 = time.perf_counter()
        result = self.benchmark_engine.run_benchmark(name, test_func, iterations)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("benchmarks_run", 1)
        self._metrics.histogram("benchmark_time_ms", elapsed)
        return result

    async def compare_benchmarks(self, baseline: str, current: str) -> Dict[str, Any]:
        if not self.benchmark_engine:
            raise RuntimeError("ImprovementService not initialized")
        return self.benchmark_engine.compare(baseline, current)

    async def check_regression(self, name: str, threshold: float = 0.1) -> bool:
        if not self.benchmark_engine:
            raise RuntimeError("ImprovementService not initialized")
        return self.benchmark_engine.check_regression(name, threshold)

    async def generate_benchmark_report(self) -> str:
        if not self.benchmark_engine:
            raise RuntimeError("ImprovementService not initialized")
        return self.benchmark_engine.generate_report()

    # ── Prompt Refinement ─────────────────────────────────────────

    async def register_prompt(self, name: str, content: str) -> PromptVersion:
        if not self.prompt_refiner:
            raise RuntimeError("ImprovementService not initialized")
        pv = self.prompt_refiner.register_prompt(name, content)
        self._metrics.counter("prompts_registered", 1)
        return pv

    async def get_active_prompt(self, name: str) -> Optional[PromptVersion]:
        if not self.prompt_refiner:
            raise RuntimeError("ImprovementService not initialized")
        return self.prompt_refiner.get_active_prompt(name)

    async def propose_refinement(
        self, name: str, new_content: str, reason: str = ""
    ) -> Optional[PromptVersion]:
        if not self.prompt_refiner:
            raise RuntimeError("ImprovementService not initialized")
        pv = self.prompt_refiner.propose_refinement(name, new_content, reason)
        if pv:
            self._metrics.counter("prompts_refined", 1)
        return pv

    async def activate_prompt_version(self, name: str, version: int) -> bool:
        if not self.prompt_refiner:
            raise RuntimeError("ImprovementService not initialized")
        return self.prompt_refiner.activate_version(name, version)

    async def rollback_prompt(self, name: str) -> bool:
        if not self.prompt_refiner:
            raise RuntimeError("ImprovementService not initialized")
        return self.prompt_refiner.rollback_prompt(name)

    # ── A/B Testing ───────────────────────────────────────────────

    async def create_ab_test(
        self,
        name: str,
        variant_a: Dict[str, Any],
        variant_b: Dict[str, Any],
        metric: str = "accuracy",
    ) -> ABTest:
        if not self.ab_test_runner:
            raise RuntimeError("A/B testing is disabled")
        test = self.ab_test_runner.create_test(name, variant_a, variant_b, metric)
        self._metrics.counter("ab_tests_created", 1)
        return test

    async def record_ab_result(self, test_id: str, variant: str, outcome: Dict[str, Any]) -> bool:
        if not self.ab_test_runner:
            raise RuntimeError("A/B testing is disabled")
        return self.ab_test_runner.record_result(test_id, variant, outcome)

    async def analyze_ab_test(self, test_id: str) -> Dict[str, Any]:
        if not self.ab_test_runner:
            raise RuntimeError("A/B testing is disabled")
        return self.ab_test_runner.analyze(test_id)

    async def complete_ab_test(self, test_id: str) -> Optional[ABTest]:
        if not self.ab_test_runner:
            raise RuntimeError("A/B testing is disabled")
        test = self.ab_test_runner.complete_test(test_id)
        if test:
            self._metrics.counter("ab_tests_completed", 1)
        return test

    # ── Health / Stats ────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        feedback_count = len(self.feedback_collector.list_feedback()) if self.feedback_collector else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "feedback_count": feedback_count,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "metrics": self._metrics.snapshot(),
        }

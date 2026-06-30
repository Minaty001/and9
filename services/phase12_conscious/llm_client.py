"""
Phase 12 — LLM Client.

Provider-agnostic LLM invocation with retry logic, error handling,
token tracking, and cost estimation.
"""

from __future__ import annotations

import json
import time
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Awaitable

from .config import ConsciousConfig
from .models import Message, Role, UsageStats, Conversation

logger = logging.getLogger(__name__)


# ── Exception hierarchy ─────────────────────────────────────────────


class LLMError(Exception):
    """Base LLM error."""
    pass


class LLMConnectionError(LLMError):
    """Connection/network error."""
    pass


class LLMTimeoutError(LLMError):
    """Request timed out."""
    pass


class LLMRateLimitError(LLMError):
    """Rate limited."""
    pass


class LLMAuthError(LLMError):
    """Authentication error."""
    pass


class LLMBadRequestError(LLMError):
    """Bad request (invalid params, content filter)."""
    pass


# ── Response model ──────────────────────────────────────────────────


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    content: str
    usage: UsageStats
    model: str
    finish_reason: str = "stop"
    raw: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0


# ── Provider interface ──────────────────────────────────────────────

CompletionFunc = Callable[[List[Dict[str, Any]], float, int], Awaitable[LLMResponse]]


class LLMClient:
    """Provider-agnostic LLM client with retry logic.

    Supports OpenAI, Anthropic, and local (HTTP) providers.
    """

    def __init__(self, config: ConsciousConfig):
        self.config = config
        self._api_key: str = ""
        self._total_cost: float = 0.0
        self._total_prompt_tokens: int = 0
        self._total_completion_tokens: int = 0
        self._retry_count: int = 0

    # ── Initialization ────────────────────────────────────────────

    def initialize(self) -> bool:
        """Load API key from environment."""
        try:
            env_var = self.config.api_key_env
            key = os.environ.get(env_var, "")
            if not key and self.config.provider != "local":
                logger.warning(
                    "API key env var '%s' not set; LLM calls will fail",
                    env_var,
                )
            self._api_key = key
            return True
        except Exception as e:
            logger.error("LLMClient init failed: %s", e)
            return False

    # ── Public API ────────────────────────────────────────────────

    async def complete(
        self,
        conversation: Conversation,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send a conversation to the LLM and return the response.

        Args:
            conversation: The conversation (system prompt + messages).
            temperature: Override config temperature.
            max_tokens: Override config max_tokens.

        Returns:
            LLMResponse with content and usage stats.

        Raises:
            LLMError subclass on failure after retries.
        """
        messages = self._build_messages(conversation)
        temp = temperature if temperature is not None else self.config.temperature
        mt = max_tokens if max_tokens is not None else self.config.max_tokens

        last_error: Optional[Exception] = None
        t0 = time.perf_counter()

        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = await self._invoke_provider(messages, temp, mt)
                response.duration_ms = (time.perf_counter() - t0) * 1000

                # Track usage
                if self.config.track_usage:
                    self._track_usage(response.usage)
                    if response.usage.estimated_cost_usd > self.config.max_cost_per_call:
                        logger.warning(
                            "LLM call cost $%.4f exceeds max $%.2f",
                            response.usage.estimated_cost_usd,
                            self.config.max_cost_per_call,
                        )

                return response

            except (LLMConnectionError, LLMTimeoutError, LLMRateLimitError) as e:
                last_error = e
                self._retry_count += 1
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay_ms * (2 ** (attempt - 1)) / 1000
                    logger.warning(
                        "LLM attempt %d/%d failed: %s. Retrying in %.1fs...",
                        attempt, self.config.max_retries, e, delay,
                    )
                    await self._sleep(delay)
                else:
                    logger.error("LLM all %d retries exhausted: %s", self.config.max_retries, e)
                    raise

            except (LLMAuthError, LLMBadRequestError) as e:
                # Non-retriable errors
                last_error = e
                logger.error("LLM non-retriable error: %s", e)
                raise

            except Exception as e:
                last_error = e
                logger.error("LLM unexpected error: %s", e)
                raise LLMError(f"Unexpected LLM error: {e}") from e

        # Should not reach here, but just in case
        raise last_error or LLMError("Unknown LLM error")

    async def complete_str(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> str:
        """Shortcut: send a single-turn prompt and return content string."""
        conv = Conversation(system_prompt=system_prompt)
        conv.add_message(Role.USER, user_prompt)
        response = await self.complete(conv, **kwargs)
        return response.content

    # ── Stats ─────────────────────────────────────────────────────

    def get_usage_summary(self) -> Dict[str, Any]:
        """Return accumulated usage summary."""
        return {
            "total_prompt_tokens": self._total_prompt_tokens,
            "total_completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
            "total_cost_usd": round(self._total_cost, 6),
            "retry_count": self._retry_count,
            "provider": self.config.provider,
            "model": self.config.model,
        }

    def reset_usage(self) -> None:
        """Reset accumulated usage counters."""
        self._total_cost = 0.0
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._retry_count = 0

    # ── Internal helpers ──────────────────────────────────────────

    def _build_messages(self, conversation: Conversation) -> List[Dict[str, Any]]:
        """Convert Conversation to provider message format."""
        messages: List[Dict[str, Any]] = []

        if conversation.system_prompt:
            messages.append({
                "role": "system",
                "content": conversation.system_prompt,
            })

        for msg in conversation.messages:
            entry: Dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }
            if msg.name:
                entry["name"] = msg.name
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            messages.append(entry)

        return messages

    async def _invoke_provider(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Route to the actual provider implementation."""
        provider = self.config.provider.lower()

        if provider == "openai":
            return await self._invoke_openai(messages, temperature, max_tokens)
        elif provider == "anthropic":
            return await self._invoke_anthropic(messages, temperature, max_tokens)
        elif provider == "local":
            return await self._invoke_local(messages, temperature, max_tokens)
        else:
            raise LLMBadRequestError(f"Unknown provider: {provider}")

    async def _invoke_openai(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Invoke OpenAI-compatible API."""
        if not self._api_key:
            raise LLMAuthError("OpenAI API key not configured")

        import httpx

        url = self.config.api_base or "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_ms / 1000) as client:
                resp = await client.post(url, headers=headers, json=body)
        except httpx.TimeoutException:
            raise LLMTimeoutError("OpenAI request timed out")
        except httpx.ConnectError as e:
            raise LLMConnectionError(f"OpenAI connection failed: {e}")
        except Exception as e:
            raise LLMConnectionError(f"OpenAI request failed: {e}")

        return self._parse_openai_response(resp.status_code, resp.text)

    def _parse_openai_response(self, status: int, text: str) -> LLMResponse:
        """Parse OpenAI response."""
        if status == 401:
            raise LLMAuthError("Invalid API key")
        if status == 429:
            raise LLMRateLimitError("Rate limited")
        if status == 400:
            raise LLMBadRequestError(f"Bad request: {text}")
        if status != 200:
            raise LLMError(f"OpenAI returned {status}: {text}")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"Invalid JSON response: {e}")

        choice = data["choices"][0]
        content = choice.get("message", {}).get("content", "") or ""
        finish_reason = choice.get("finish_reason", "stop")

        usage_data = data.get("usage", {})
        usage = UsageStats(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
            provider="openai",
            model=self.config.model,
        )
        usage.calculate_cost()

        return LLMResponse(
            content=content,
            usage=usage,
            model=self.config.model,
            finish_reason=finish_reason,
            raw=data,
        )

    async def _invoke_anthropic(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Invoke Anthropic API."""
        if not self._api_key:
            raise LLMAuthError("Anthropic API key not configured")

        import httpx

        url = self.config.api_base or "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        # Convert OpenAI format to Anthropic format
        system = ""
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                anthropic_messages.append(m)

        body: Dict[str, Any] = {
            "model": self.config.model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            body["system"] = system

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_ms / 1000) as client:
                resp = await client.post(url, headers=headers, json=body)
        except httpx.TimeoutException:
            raise LLMTimeoutError("Anthropic request timed out")
        except httpx.ConnectError as e:
            raise LLMConnectionError(f"Anthropic connection failed: {e}")
        except Exception as e:
            raise LLMConnectionError(f"Anthropic request failed: {e}")

        return self._parse_anthropic_response(resp.status_code, resp.text)

    def _parse_anthropic_response(self, status: int, text: str) -> LLMResponse:
        """Parse Anthropic response."""
        if status == 401:
            raise LLMAuthError("Invalid API key")
        if status == 429:
            raise LLMRateLimitError("Rate limited")
        if status != 200:
            raise LLMError(f"Anthropic returned {status}: {text}")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"Invalid JSON response: {e}")

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        usage_data = data.get("usage", {})
        usage = UsageStats(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
            total_tokens=(usage_data.get("input_tokens", 0)
                          + usage_data.get("output_tokens", 0)),
            provider="anthropic",
            model=self.config.model,
        )
        usage.calculate_cost()

        return LLMResponse(
            content=content,
            usage=usage,
            model=self.config.model,
            finish_reason="stop",
            raw=data,
        )

    async def _invoke_local(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Invoke a local HTTP endpoint (e.g., Ollama, vLLM)."""
        import httpx

        url = self.config.api_base or "http://localhost:11434/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        body = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_ms / 1000) as client:
                resp = await client.post(url, headers=headers, json=body)
        except httpx.TimeoutException:
            raise LLMTimeoutError("Local LLM request timed out")
        except httpx.ConnectError as e:
            raise LLMConnectionError(f"Local LLM connection failed: {e}")
        except Exception as e:
            raise LLMConnectionError(f"Local LLM request failed: {e}")

        return self._parse_openai_response(resp.status_code, resp.text)

    def _track_usage(self, usage: UsageStats) -> None:
        """Accumulate usage statistics."""
        self._total_prompt_tokens += usage.prompt_tokens
        self._total_completion_tokens += usage.completion_tokens
        self._total_cost += usage.estimated_cost_usd

    async def _sleep(self, seconds: float) -> None:
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(seconds)

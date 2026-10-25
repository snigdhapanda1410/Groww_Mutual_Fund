"""Groq LLM Client with deterministic generation, rate limiting, and exponential backoff retries."""

import time
from collections import deque
from datetime import date
from typing import Any, Deque, Dict, Optional, Tuple

import groq
from groq import Groq
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Sliding-window rate limiter enforcing RPM, TPM, RPD, and TPD quotas."""

    def __init__(
        self,
        rpm_limit: int = 30,
        tpm_limit: int = 8000,
        rpd_limit: int = 1000,
        tpd_limit: int = 200000,
    ):
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.rpd_limit = rpd_limit
        self.tpd_limit = tpd_limit

        self._request_window: Deque[float] = deque()
        self._token_window: Deque[Tuple[float, int]] = deque()
        self._daily_requests: int = 0
        self._daily_tokens: int = 0
        self._current_date: date = date.today()

    def _reset_daily_if_new_day(self) -> None:
        today = date.today()
        if today != self._current_date:
            self._daily_requests = 0
            self._daily_tokens = 0
            self._current_date = today

    def acquire(self, estimated_tokens: int = 500) -> None:
        """Enforce rate limits before dispatching request. Sleeps if near rate limit."""
        self._reset_daily_if_new_day()
        now = time.time()

        # Clean old records (> 60s)
        while self._request_window and now - self._request_window[0] >= 60.0:
            self._request_window.popleft()
        while self._token_window and now - self._token_window[0][0] >= 60.0:
            self._token_window.popleft()

        # Check RPM
        if len(self._request_window) >= self.rpm_limit:
            wait_time = 60.0 - (now - self._request_window[0]) + 0.1
            if wait_time > 0:
                logger.warning(
                    f"Approaching RPM limit ({self.rpm_limit} req/min). Throttling for {wait_time:.2f}s."
                )
                time.sleep(wait_time)
                now = time.time()

        # Check TPM
        current_tpm = sum(t[1] for t in self._token_window)
        if current_tpm + estimated_tokens > self.tpm_limit and self._token_window:
            wait_time = 60.0 - (now - self._token_window[0][0]) + 0.1
            if wait_time > 0:
                logger.warning(
                    f"Approaching TPM limit ({self.tpm_limit} tok/min). Throttling for {wait_time:.2f}s."
                )
                time.sleep(wait_time)

    def record(self, tokens_used: int) -> None:
        """Record completed request and token usage."""
        self._reset_daily_if_new_day()
        now = time.time()
        self._request_window.append(now)
        self._token_window.append((now, tokens_used))
        self._daily_requests += 1
        self._daily_tokens += tokens_used

    def get_stats(self) -> Dict[str, Any]:
        """Return current usage statistics."""
        self._reset_daily_if_new_day()
        now = time.time()
        active_rpm = len([t for t in self._request_window if now - t < 60.0])
        active_tpm = sum(tok for t, tok in self._token_window if now - t < 60.0)
        return {
            "active_rpm": active_rpm,
            "rpm_limit": self.rpm_limit,
            "active_tpm": active_tpm,
            "tpm_limit": self.tpm_limit,
            "daily_requests": self._daily_requests,
            "rpd_limit": self.rpd_limit,
            "daily_tokens": self._daily_tokens,
            "tpd_limit": self.tpd_limit,
        }


# Singleton rate limiter instance
rate_limiter = RateLimiter(
    rpm_limit=config.llm_rpm_limit,
    tpm_limit=config.llm_tpm_limit,
    rpd_limit=config.llm_rpd_limit,
    tpd_limit=config.llm_tpd_limit,
)

_groq_client_instance: Optional[Groq] = None


def get_groq_client() -> Groq:
    """Retrieve or initialize the Groq client instance."""
    global _groq_client_instance
    if _groq_client_instance is None:
        api_key = config.groq_api_key or "mock_key_for_offline_eval"
        _groq_client_instance = Groq(api_key=api_key)
    return _groq_client_instance


def set_groq_client(client: Optional[Groq]) -> None:
    """Override Groq client for testing or custom mocks."""
    global _groq_client_instance
    _groq_client_instance = client


@retry(
    retry=retry_if_exception_type((groq.RateLimitError, groq.APIConnectionError, groq.APITimeoutError)),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
def generate(
    prompt: str,
    client: Optional[Any] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """Execute chat completion with retry backoff and token limit monitoring.
    
    Args:
        prompt: Formatted prompt text for the LLM.
        client: Optional Groq client override.
        model: Model name override (defaults to config.groq_model, i.e. openai/gpt-oss-120b).
        temperature: Temperature override (defaults to 0.0).
        top_p: Top_p override (defaults to 0.1).
        max_tokens: Token ceiling override (defaults to config.llm_max_output_tokens = 300).
        
    Returns:
        Generated text response string.
    """
    target_client = client or get_groq_client()
    target_model = model or config.groq_model
    target_temp = temperature if temperature is not None else config.llm_temperature
    target_top_p = top_p if top_p is not None else config.llm_top_p
    target_max_tokens = max_tokens or config.llm_max_output_tokens

    # Rate limiter check (30 RPM, 8K TPM)
    rate_limiter.acquire(estimated_tokens=target_max_tokens)

    start_time = time.perf_counter()
    try:
        chat_completion = target_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=target_model,
            temperature=target_temp,
            top_p=target_top_p,
            max_tokens=target_max_tokens,
        )
    except Exception as e:
        logger.error(f"Groq API call error on model '{target_model}': {e}")
        raise

    latency_ms = (time.perf_counter() - start_time) * 1000
    choice = chat_completion.choices[0]
    raw_content = choice.message.content or ""

    usage = getattr(chat_completion, "usage", None)
    if usage and hasattr(usage, "total_tokens") and usage.total_tokens:
        total_tokens = usage.total_tokens
    else:
        total_tokens = len(prompt.split()) + len(raw_content.split())

    rate_limiter.record(tokens_used=total_tokens)

    logger.info(
        f"Groq response from '{target_model}' in {latency_ms:.1f}ms: "
        f"{total_tokens} tokens, snippet='{raw_content[:60]}...'"
    )

    return raw_content.strip()


def generate_intent_classification(query: str, client: Optional[Any] = None) -> str:
    """Fast single-token intent classification call to distinguish advisory vs factual queries."""
    from src.generation.prompt_templates import build_refusal_prompt

    prompt = build_refusal_prompt(query)
    try:
        response = generate(prompt, client=client, max_tokens=10)
        return response.strip().upper()
    except Exception as e:
        logger.warning(
            f"Intent classification LLM call failed: {e}; defaulting to FACTUAL"
        )
        return "FACTUAL"

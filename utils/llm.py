"""LLM provider factory — one place to construct the chat model.

The PRD locks OpenAI (ADR-0001), but the project temporarily runs on Groq while
the OpenAI key is inactive (ADR-0009). Both are OpenAI-compatible chat models, so
switching is a one-line change: set ``LLM_PROVIDER`` in ``.env``. Nodes never
import a provider directly — they call :func:`get_llm`, keeping the swap trivial.

Design for testability: nodes accept an injected model, so unit tests pass a stub
and never hit the network. :func:`get_llm` is only invoked when wiring the real
graph or running live.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import config

if TYPE_CHECKING:  # avoid importing heavy/optional providers at module load
    from langchain_core.language_models.chat_models import BaseChatModel

# OpenAI reasoning-family models that reject a non-default ``temperature``.
_OPENAI_FIXED_TEMPERATURE_PREFIXES: tuple[str, ...] = ("gpt-5", "o1", "o3", "o4")

# Substrings that mark a transient LLM error worth retrying (rate limits, overload,
# provider blips). Everything else fails fast so the node's fallback path runs.
_TRANSIENT_LLM_HINTS: tuple[str, ...] = (
    "429", "rate limit", "rate_limit", "too many requests", "overloaded",
    "temporarily", "unavailable", "timeout", "timed out", "503", "502", "500",
)


def invoke_structured(
    llm: BaseChatModel,
    schema: type,
    prompt: str,
    *,
    max_retries: int = 5,
    base_delay: float = 5.0,
    sleep: Any = time.sleep,
) -> Any:
    """Call ``llm.with_structured_output(schema).invoke(prompt)`` with retry.

    Retries only on **transient** errors (rate limits / provider overload) with
    linear backoff; non-transient errors raise immediately so the caller's
    degradation path handles them. This keeps a burst of eval calls from collapsing
    when the provider rate-limits.
    """
    structured = llm.with_structured_output(schema)
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return structured.invoke(prompt)
        except Exception as exc:  # noqa: BLE001 - inspected below
            last_exc = exc
            transient = any(h in str(exc).lower() for h in _TRANSIENT_LLM_HINTS)
            if attempt < max_retries and transient:
                sleep(base_delay * (attempt + 1))
                continue
            raise
    assert last_exc is not None  # unreachable
    raise last_exc


def get_llm(temperature: float | None = None, **kwargs: Any) -> BaseChatModel:
    """Construct the configured chat model.

    Reads ``config.LLM_PROVIDER`` (``"openai"`` or ``"groq"``) and the matching
    model id. ``temperature`` defaults to ``config.LLM_TEMPERATURE``; it is omitted
    automatically for OpenAI reasoning models that only allow the default.

    Raises ``ValueError`` for an unknown provider and a clear ``RuntimeError`` if
    the provider's API key is missing.
    """
    provider = config.LLM_PROVIDER
    temp = config.LLM_TEMPERATURE if temperature is None else temperature

    if provider == "groq":
        _require_key("GROQ_API_KEY", provider)
        from langchain_groq import ChatGroq

        return ChatGroq(model=config.GROQ_MODEL, temperature=temp, **kwargs)

    if provider == "openai":
        _require_key("OPENAI_API_KEY", provider)
        from langchain_openai import ChatOpenAI

        model = config.OPENAI_MODEL
        if model.startswith(_OPENAI_FIXED_TEMPERATURE_PREFIXES):
            # These models reject an explicit temperature; use the server default.
            return ChatOpenAI(model=model, **kwargs)
        return ChatOpenAI(model=model, temperature=temp, **kwargs)

    raise ValueError(
        f"Unknown LLM_PROVIDER {provider!r}; expected 'openai' or 'groq'."
    )


def _require_key(env_var: str, provider: str) -> None:
    """Raise a helpful error if the provider's API key is not set."""
    import os

    if not os.getenv(env_var):
        raise RuntimeError(
            f"{env_var} is not set, but LLM_PROVIDER={provider!r}. "
            f"Add {env_var} to your .env (copy .env.example)."
        )

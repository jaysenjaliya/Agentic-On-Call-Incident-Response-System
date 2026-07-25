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

from typing import TYPE_CHECKING, Any

import config

if TYPE_CHECKING:  # avoid importing heavy/optional providers at module load
    from langchain_core.language_models.chat_models import BaseChatModel

# OpenAI reasoning-family models that reject a non-default ``temperature``.
_OPENAI_FIXED_TEMPERATURE_PREFIXES: tuple[str, ...] = ("gpt-5", "o1", "o3", "o4")


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

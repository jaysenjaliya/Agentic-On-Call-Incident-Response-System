"""Test doubles shared across subgraph tests.

``StubLLM`` mimics the slice of the LangChain chat-model interface the nodes use
(``with_structured_output(schema).invoke(...)`` and ``.invoke(...)``) so unit
tests are deterministic and never hit the network.
"""

from __future__ import annotations

from typing import Any


class _StructuredStub:
    def __init__(self, result: Any, raise_exc: Exception | None) -> None:
        self._result = result
        self._raise = raise_exc

    def invoke(self, *_args: Any, **_kwargs: Any) -> Any:
        if self._raise is not None:
            raise self._raise
        return self._result


class StubLLM:
    """A stand-in chat model returning a preset structured result (or raising)."""

    def __init__(self, structured_result: Any = None, raise_exc: Exception | None = None) -> None:
        self._structured_result = structured_result
        self._raise = raise_exc

    def with_structured_output(self, _schema: Any, **_kwargs: Any) -> _StructuredStub:
        return _StructuredStub(self._structured_result, self._raise)

    def invoke(self, *_args: Any, **_kwargs: Any) -> Any:
        if self._raise is not None:
            raise self._raise
        return self._structured_result

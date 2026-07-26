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


class PhaseStubLLM:
    """Full-pipeline stub: returns the right schema per node (diagnosis vs root cause).

    Lets supervisor tests drive an end-to-end run offline with a chosen severity and
    confidence, so routing (auto-fix / HITL / escalate) is deterministic.
    """

    def __init__(
        self, *, severity: str = "P1", confidence: float = 0.9, runbook_id: str | None = "RB-101",
        failing_component: str = "DB pool", blast_radius: str = "checkout users",
        diagnosis_summary: str = "pool exhausted", hypothesis: str = "pool too small",
    ) -> None:
        self.severity = severity
        self.confidence = confidence
        self.runbook_id = runbook_id
        self.failing_component = failing_component
        self.blast_radius = blast_radius
        self.diagnosis_summary = diagnosis_summary
        self.hypothesis = hypothesis

    def with_structured_output(self, schema: Any, **_kwargs: Any) -> Any:
        outer = self

        class _R:
            def invoke(self, *_a: Any, **_k: Any) -> Any:
                if schema.__name__ == "DiagnosisResult":
                    return schema(
                        failing_component=outer.failing_component, blast_radius=outer.blast_radius,
                        severity=outer.severity, summary=outer.diagnosis_summary,
                    )
                if schema.__name__ == "RootCauseResult":
                    return schema(
                        hypothesis=outer.hypothesis, confidence=outer.confidence,
                        matched_runbook_id=outer.runbook_id,
                    )
                raise AssertionError(f"unexpected schema {schema.__name__}")

        return _R()

    def invoke(self, *_a: Any, **_k: Any) -> Any:
        return None

"""Tests for AgentBase — the abstract interface every agent implements."""

from __future__ import annotations

import pytest

from agents.common.base_agent import AgentBase, BaseAgent
from agents.common.event_envelope import EventEnvelope


class _ConcreteAgent(AgentBase):
    """Minimal concrete subclass for testing the ABC pattern."""

    def __init__(self, agent_id: str = "test-agent") -> None:
        self._agent_id = agent_id

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def health_check(self) -> dict:
        return {"status": "ok", "agent": self.agent_id}

    def process(self, event: EventEnvelope) -> EventEnvelope | None:
        return event


class TestAgentBase:
    """Verify the abstract interface and agent_id storage."""

    def test_cannot_instantiate_abc(self) -> None:
        """AgentBase cannot be instantiated directly (it's an ABC)."""
        with pytest.raises(TypeError):
            AgentBase()  # type: ignore[abstract]

    def test_agent_id_property(self) -> None:
        """The agent_id property returns the value set by the subclass."""
        agent = _ConcreteAgent(agent_id="my-custom-agent")
        assert agent.agent_id == "my-custom-agent"

    def test_health_check_callable(self) -> None:
        """A concrete subclass can call health_check()."""
        agent = _ConcreteAgent()
        result = agent.health_check()
        assert result["status"] == "ok"

    def test_process_callable(self) -> None:
        """A concrete subclass can call process()."""
        agent = _ConcreteAgent()
        event = EventEnvelope(
            correlation_id="c-1", agent_id="test", payload={}
        )
        out = agent.process(event)
        assert out is not None
        assert out.correlation_id == "c-1"

    def test_backward_compat_alias(self) -> None:
        """BaseAgent is an alias for AgentBase."""
        assert BaseAgent is AgentBase

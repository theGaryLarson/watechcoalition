"""Tests for NormalizationAgent — updated for Week 3 implementation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agents.common.event_envelope import EventEnvelope
from agents.normalization.agent import NormalizationAgent


class TestNormalizationAgent:
    """Verify agent_id, health_check, and process behaviour."""

    def test_agent_id(self) -> None:
        agent = NormalizationAgent()
        assert agent.agent_id == "normalization-agent"

    def test_health_check_shape(self) -> None:
        """Health check returns dict with required keys."""
        agent = NormalizationAgent()
        result = agent.health_check()
        assert "status" in result
        assert result["status"] in ("ok", "degraded", "down")
        assert result["agent"] == "normalization-agent"
        assert "db_reachable" in result

    @patch("agents.normalization.agent.session_scope")
    @patch("agents.normalization.agent.check_db_connection", return_value=True)
    def test_process_empty_batch(self, mock_db, mock_session) -> None:
        """Empty pending records returns NormalizationComplete with 0 counts."""
        # Mock session_scope to return a session with no pending records
        mock_sess = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_sess.query.return_value = mock_query
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_sess)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        agent = NormalizationAgent()
        event = EventEnvelope(
            correlation_id="test-1",
            agent_id="ingestion-agent",
            payload={
                "event_type": "IngestBatch",
                "batch_id": "test-batch",
            },
        )
        out = agent.process(event)
        assert out.payload["event_type"] == "NormalizationComplete"
        assert out.agent_id == "normalization-agent"
        assert out.payload["normalized_count"] == 0

    @patch("agents.normalization.agent.session_scope")
    @patch("agents.normalization.agent.check_db_connection", return_value=True)
    def test_process_preserves_correlation_id(self, mock_db, mock_session) -> None:
        """Correlation ID passes through unchanged."""
        mock_sess = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_sess.query.return_value = mock_query
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_sess)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        agent = NormalizationAgent()
        event = EventEnvelope(
            correlation_id="test-1",
            agent_id="ingestion-agent",
            payload={
                "event_type": "IngestBatch",
                "batch_id": "test-batch",
            },
        )
        out = agent.process(event)
        assert out.correlation_id == "test-1"

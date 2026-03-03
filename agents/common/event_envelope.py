"""
EventEnvelope — the typed event contract shared by every agent in the pipeline.

Every agent receives an EventEnvelope and returns an EventEnvelope.
The six fields below are required on every event, regardless of what
is in the payload.

Week 2 walking skeleton: all six fields are live from day one.
The payload shape varies by agent; see each agent's module docstring
and the fixture files for examples.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import secrets

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """
    Typed, versioned event contract for the Job Intelligence Engine pipeline.

    Fields
    ------
    event_id       : Unique identifier for this specific event (UUID4).
                     Generated automatically; never reused.

    correlation_id : Ties all events produced by a single pipeline run for
                     one job record together.  Set once by the pipeline runner
                     when the record enters the pipeline; carried through every
                     subsequent agent unchanged.

    agent_id       : Canonical identifier of the agent that produced this event.
                     Must match the agent_id defined in ARCHITECTURE_DEEP.md.

    timestamp      : UTC datetime this event was produced.

    schema_version : Version of this event contract.  Increment on breaking
                     changes to the six required fields.

    payload        : Agent-specific data.  Shape varies by agent; see each
                     agent's module docstring and the fixture files for
                     concrete examples.
    """

    event_id: str = Field(
        default_factory=lambda: _uuid4_str(),
    )
    correlation_id: str
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    schema_version: str = "1.0"
    payload: dict[str, Any]


def _uuid4_str() -> str:
    """
    Generate a UUID4-compatible string without importing the stdlib uuid module.

    This helper avoids importing the standard library `uuid` module, which
    internally imports `platform` and can be disrupted by third-party packages
    that shadow or partially implement the `platform` module. The generated
    identifiers conform to the UUID v4 bit layout and are suitable for use as
    event identifiers within the pipeline.
    """
    random_bytes = bytearray(secrets.token_bytes(16))
    random_bytes[6] = (random_bytes[6] & 0x0F) | 0x40  # version 4
    random_bytes[8] = (random_bytes[8] & 0x3F) | 0x80  # variant 10xx
    hexed = random_bytes.hex()
    return (
        f"{hexed[0:8]}-"
        f"{hexed[8:12]}-"
        f"{hexed[12:16]}-"
        f"{hexed[16:20]}-"
        f"{hexed[20:32]}"
    )

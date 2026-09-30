from typing import Literal

from pydantic import BaseModel, Field


class Event(BaseModel):
    time: str
    device: str
    alarm: str
    current_a: float


class Answer(BaseModel):
    answer: str
    events: list[Event] = Field(default_factory=list)
    cause: str | None = None
    sources: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    escalate: bool = False


class Result(BaseModel):
    question: str
    answer: Answer | None
    escalated: bool
    reasons: list[str]
    notes: list[int]
    tools: list[str]
    trace_id: str

"""Data models for mystery shopping sessions."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import json
import uuid


class Channel(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    WEBCHAT = "webchat"


class TestStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_RESPONSE = "waiting_response"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScoreItem:
    criterion: str
    score: int  # 0-100
    max_score: int = 100
    notes: str = ""
    passed: bool = False

    def __post_init__(self):
        self.passed = self.score >= 60


@dataclass
class ChannelResult:
    channel: Channel
    status: TestStatus = TestStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Raw interaction data
    outbound_content: str = ""  # What we sent/said
    inbound_content: str = ""  # What they replied

    # Timing
    response_time_seconds: Optional[float] = None

    # Scores
    scores: list[ScoreItem] = field(default_factory=list)
    overall_score: int = 0
    summary: str = ""
    strengths: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)


@dataclass
class Target:
    name: str
    industry: str = "hotel"
    email: Optional[str] = None
    phone: Optional[str] = None
    webchat_url: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class MysteryShopSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    target: Target = field(default_factory=lambda: Target(name="Unknown"))
    scenario_name: str = "default"
    created_at: datetime = field(default_factory=datetime.now)
    results: dict[str, ChannelResult] = field(default_factory=dict)

    @property
    def overall_score(self) -> int:
        if not self.results:
            return 0
        completed = [r for r in self.results.values() if r.status == TestStatus.COMPLETED]
        if not completed:
            return 0
        return int(sum(r.overall_score for r in completed) / len(completed))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target": {
                "name": self.target.name,
                "industry": self.target.industry,
                "email": self.target.email,
                "phone": self.target.phone,
            },
            "scenario": self.scenario_name,
            "created_at": self.created_at.isoformat(),
            "overall_score": self.overall_score,
            "channels": {
                name: {
                    "channel": r.channel.value,
                    "status": r.status.value,
                    "response_time_seconds": r.response_time_seconds,
                    "overall_score": r.overall_score,
                    "summary": r.summary,
                    "strengths": r.strengths,
                    "improvements": r.improvements,
                    "scores": [
                        {"criterion": s.criterion, "score": s.score, "passed": s.passed, "notes": s.notes}
                        for s in r.scores
                    ],
                }
                for name, r in self.results.items()
            },
        }

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

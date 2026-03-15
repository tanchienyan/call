"""Journey Orchestrator — the brain of AI Mystery Shopper.

Orchestrates a full customer journey across multiple channels:
  Website visit → Webchat → Email → Phone → WhatsApp → Follow-up monitoring

Each step feeds context to the next, creating a realistic multi-touch
customer simulation that tests the entire service experience.
"""

import json
import time
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable
from pathlib import Path


class StepType(str, Enum):
    BROWSE_WEBSITE = "browse_website"
    WEBCHAT = "webchat"
    SEND_EMAIL = "send_email"
    WAIT_EMAIL = "wait_email"
    PHONE_CALL = "phone_call"
    SEND_WHATSAPP = "send_whatsapp"
    WAIT_WHATSAPP = "wait_whatsapp"
    SEND_INSTAGRAM = "send_instagram"
    WAIT_FOLLOWUP = "wait_followup"
    ANALYZE = "analyze"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class StepResult:
    step_name: str
    step_type: StepType
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    data_sent: str = ""
    data_received: str = ""
    response_time_seconds: Optional[float] = None
    screenshots: list[str] = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    notes: str = ""
    context_for_next: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "step_name": self.step_name,
            "step_type": self.step_type.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "data_sent": self.data_sent[:500],
            "data_received": self.data_received[:500],
            "response_time_seconds": self.response_time_seconds,
            "screenshots": self.screenshots,
            "scores": self.scores,
            "notes": self.notes,
        }


@dataclass
class JourneyStep:
    """A single step in the customer journey."""
    name: str
    step_type: StepType
    config: dict = field(default_factory=dict)
    condition: Optional[str] = None  # e.g., "previous.context_for_next.got_email == True"
    timeout_seconds: int = 300
    retry_count: int = 0


@dataclass
class JourneyPlan:
    """A complete customer journey plan."""
    name: str
    description: str
    persona: dict = field(default_factory=dict)
    target: dict = field(default_factory=dict)
    steps: list[JourneyStep] = field(default_factory=list)

    @classmethod
    def hotel_full_journey(cls, target_name: str, target_website: str,
                           target_email: str = "", target_phone: str = "",
                           target_whatsapp: str = ""):
        """Create a full hotel mystery shopping journey."""
        steps = []

        # Step 1: Browse website
        steps.append(JourneyStep(
            name="Browse Hotel Website",
            step_type=StepType.BROWSE_WEBSITE,
            config={
                "url": target_website,
                "tasks": [
                    "Navigate to the hotel website",
                    "Look for room types and rates",
                    "Check if there's a booking widget",
                    "Look for contact information",
                    "Check for a live chat widget",
                    "Take screenshots of key pages",
                ],
                "extract": ["room_types", "rate_range", "has_chat", "has_booking", "contact_info"],
            },
        ))

        # Step 2: Webchat (if available)
        steps.append(JourneyStep(
            name="Webchat Inquiry",
            step_type=StepType.WEBCHAT,
            condition="previous.context_for_next.has_chat == True",
            config={
                "message": "Hi, I'm looking to book a room for next Thursday to Sunday. Do you have any quiet rooms on a high floor available?",
                "follow_ups": [
                    "What's the rate for that?",
                    "Does it include breakfast?",
                    "Can I get late checkout?",
                ],
                "provide_email_when_asked": True,
            },
        ))

        # Step 3: Send email inquiry
        if target_email:
            steps.append(JourneyStep(
                name="Email Inquiry",
                step_type=StepType.SEND_EMAIL,
                config={
                    "to": target_email,
                    "subject": "Room availability inquiry - next Thursday to Sunday",
                    "body_template": "hotel_inquiry",
                },
            ))

            # Step 4: Wait for email reply
            steps.append(JourneyStep(
                name="Wait for Email Reply",
                step_type=StepType.WAIT_EMAIL,
                config={
                    "from_address": target_email,
                    "timeout_hours": 48,
                    "check_interval_minutes": 30,
                },
                timeout_seconds=172800,  # 48 hours
            ))

        # Step 5: Phone call
        if target_phone:
            steps.append(JourneyStep(
                name="Phone Call Inquiry",
                step_type=StepType.PHONE_CALL,
                config={
                    "phone_number": target_phone,
                    "persona": "sarah_mitchell",
                    "reference_previous": True,  # Mention "I also sent an email" if email was sent
                },
            ))

        # Step 6: WhatsApp (if available)
        if target_whatsapp:
            steps.append(JourneyStep(
                name="WhatsApp Message",
                step_type=StepType.SEND_WHATSAPP,
                config={
                    "to": target_whatsapp,
                    "message": "Hi! I spoke with someone on the phone about booking a room for next Thursday-Sunday. Could you send me a confirmation of the rates discussed? Thanks, Sarah",
                },
            ))

            steps.append(JourneyStep(
                name="Wait for WhatsApp Reply",
                step_type=StepType.WAIT_WHATSAPP,
                config={
                    "from": target_whatsapp,
                    "timeout_hours": 24,
                },
                timeout_seconds=86400,
            ))

        # Step 7: Wait for follow-up (don't reply to anything, see if they chase)
        steps.append(JourneyStep(
            name="Follow-up Monitoring",
            step_type=StepType.WAIT_FOLLOWUP,
            config={
                "monitor_channels": ["email", "whatsapp", "phone"],
                "timeout_hours": 72,
                "description": "Monitor all channels for proactive follow-up from the hotel",
            },
            timeout_seconds=259200,  # 72 hours
        ))

        # Step 8: Final analysis
        steps.append(JourneyStep(
            name="Full Journey Analysis",
            step_type=StepType.ANALYZE,
            config={
                "analyze_all_steps": True,
                "cross_channel_consistency": True,
                "generate_report": True,
            },
        ))

        return cls(
            name=f"Full Journey - {target_name}",
            description=f"Complete mystery shopping journey for {target_name}",
            persona={
                "name": "Sarah Mitchell",
                "email": "mystery_shopper_email",  # Will be filled by config
                "phone": "mystery_shopper_phone",
                "style": "Professional, polite, time-pressed business traveler",
            },
            target={
                "name": target_name,
                "website": target_website,
                "email": target_email,
                "phone": target_phone,
                "whatsapp": target_whatsapp,
            },
            steps=steps,
        )


class JourneyOrchestrator:
    """Executes a journey plan step by step."""

    def __init__(self, channel_registry: dict = None):
        """
        channel_registry: dict mapping StepType -> handler function
        Each handler takes (step: JourneyStep, context: dict) -> StepResult
        """
        self.channels = channel_registry or {}
        self.results: list[StepResult] = []
        self.context: dict = {}  # Accumulated context across steps
        self.log: list[dict] = []

    def register_channel(self, step_type: StepType, handler: Callable):
        self.channels[step_type] = handler

    def _log(self, msg: str):
        entry = {"time": datetime.now().isoformat(), "message": msg}
        self.log.append(entry)
        print(f"  [{entry['time'][:19]}] {msg}")

    async def execute(self, plan: JourneyPlan) -> list[StepResult]:
        """Execute a journey plan."""
        print(f"\n🕵️  Starting Journey: {plan.name}")
        print(f"   Persona: {plan.persona.get('name', 'Unknown')}")
        print(f"   Target: {plan.target.get('name', 'Unknown')}")
        print(f"   Steps: {len(plan.steps)}")
        print()

        self.context = {
            "persona": plan.persona,
            "target": plan.target,
            "step_results": {},
        }

        for i, step in enumerate(plan.steps):
            step_icon = {
                StepType.BROWSE_WEBSITE: "🌐",
                StepType.WEBCHAT: "💬",
                StepType.SEND_EMAIL: "📧",
                StepType.WAIT_EMAIL: "📨",
                StepType.PHONE_CALL: "📞",
                StepType.SEND_WHATSAPP: "📱",
                StepType.WAIT_WHATSAPP: "📲",
                StepType.WAIT_FOLLOWUP: "⏳",
                StepType.ANALYZE: "📊",
            }.get(step.step_type, "📋")

            print(f"{'─' * 50}")
            print(f"{step_icon} Step {i+1}/{len(plan.steps)}: {step.name}")

            # Check condition
            if step.condition and not self._evaluate_condition(step.condition):
                self._log(f"Skipping: condition not met ({step.condition})")
                result = StepResult(
                    step_name=step.name,
                    step_type=step.step_type,
                    status=StepStatus.SKIPPED,
                    notes=f"Condition not met: {step.condition}",
                )
                self.results.append(result)
                continue

            # Execute step
            handler = self.channels.get(step.step_type)
            if not handler:
                self._log(f"No handler registered for {step.step_type.value}")
                result = StepResult(
                    step_name=step.name,
                    step_type=step.step_type,
                    status=StepStatus.FAILED,
                    notes=f"No handler for {step.step_type.value}",
                )
                self.results.append(result)
                continue

            try:
                result = await handler(step, self.context)
                result.step_name = step.name
                result.step_type = step.step_type
                self.results.append(result)

                # Update context with this step's output
                self.context["step_results"][step.name] = result
                if result.context_for_next:
                    self.context.update(result.context_for_next)

                status_icon = "✅" if result.status == StepStatus.COMPLETED else "⚠️"
                self._log(f"{status_icon} {step.name}: {result.status.value}")
                if result.scores:
                    self._log(f"   Score: {result.scores.get('overall', 'N/A')}/100")

            except Exception as e:
                self._log(f"❌ Error: {str(e)}")
                result = StepResult(
                    step_name=step.name,
                    step_type=step.step_type,
                    status=StepStatus.FAILED,
                    notes=str(e),
                )
                self.results.append(result)

        print(f"\n{'═' * 50}")
        print(f"🏁 Journey Complete: {plan.name}")
        completed = [r for r in self.results if r.status == StepStatus.COMPLETED]
        if completed:
            avg = sum(r.scores.get("overall", 0) for r in completed) / len(completed)
            print(f"📊 Average Score: {avg:.0f}/100")
        print(f"{'═' * 50}\n")

        return self.results

    def _evaluate_condition(self, condition: str) -> bool:
        """Simple condition evaluator."""
        try:
            # e.g., "previous.context_for_next.has_chat == True"
            parts = condition.split("==")
            if len(parts) != 2:
                return True
            path = parts[0].strip()
            expected = parts[1].strip()

            # Navigate context
            if path.startswith("previous.context_for_next."):
                key = path.replace("previous.context_for_next.", "")
                actual = str(self.context.get(key, ""))
                return actual == expected
            return True
        except Exception:
            return True

    def get_journey_report(self) -> dict:
        """Generate a complete journey report."""
        completed = [r for r in self.results if r.status == StepStatus.COMPLETED]
        overall = 0
        if completed:
            scores = [r.scores.get("overall", 0) for r in completed if r.scores.get("overall")]
            overall = int(sum(scores) / len(scores)) if scores else 0

        return {
            "overall_score": overall,
            "steps_total": len(self.results),
            "steps_completed": len(completed),
            "steps_skipped": len([r for r in self.results if r.status == StepStatus.SKIPPED]),
            "steps_failed": len([r for r in self.results if r.status == StepStatus.FAILED]),
            "steps": [r.to_dict() for r in self.results],
            "log": self.log,
        }

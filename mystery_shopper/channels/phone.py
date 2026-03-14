"""Phone mystery shopping channel using Retell AI."""

import json
import time
from datetime import datetime
from retell import Retell

from ..config import config
from ..models import Channel, ChannelResult, TestStatus
from ..scoring.engine import score_interaction
from ..scenarios.hotel import get_phone_scenario


class PhoneMysteryShopper:
    """Make AI phone calls and score the interaction."""

    def __init__(self):
        if not config.RETELL_API_KEY:
            raise ValueError("RETELL_API_KEY is required for phone mystery shopping")
        self.client = Retell(api_key=config.RETELL_API_KEY)
        self.agent_id = None

    def create_agent(self, scenario: dict) -> str:
        """Create a Retell agent for the mystery shopping call."""
        agent = self.client.agent.create(
            agent_name=f"Mystery Shopper - {scenario['persona']['name']}",
            response_engine={
                "type": "retell-llm",
                "llm_id": self._create_llm(scenario),
            },
            voice_id="11labs-Adrian",  # Natural male voice
            language="en-US",
        )
        self.agent_id = agent.agent_id
        return agent.agent_id

    def _create_llm(self, scenario: dict) -> str:
        """Create a Retell LLM with the mystery shopper persona."""
        llm = self.client.llm.create(
            model="gpt-4o",
            general_prompt=scenario["system_prompt"],
            begin_message=f"Hi, I'm calling to inquire about booking a room at your hotel.",
            general_tools=[],
            inbound_dynamic_variables_webhook_url=None,
        )
        return llm.llm_id

    def make_call(self, phone_number: str, scenario: dict) -> ChannelResult:
        """Make a mystery shopping call."""
        result = ChannelResult(
            channel=Channel.PHONE,
            status=TestStatus.IN_PROGRESS,
            started_at=datetime.now(),
        )

        try:
            # Create agent if not exists
            if not self.agent_id:
                self.create_agent(scenario)

            # Make the call
            call = self.client.call.create_phone_call(
                from_number="+14155551234",  # Your Retell number
                to_number=phone_number,
                override_agent_id=self.agent_id,
            )

            result.outbound_content = f"AI called {phone_number} as {scenario['persona']['name']}"

            # Poll for call completion
            call_id = call.call_id
            print(f"📞 Call initiated: {call_id}")

            max_wait = 300  # 5 minutes
            poll_interval = 5
            elapsed = 0

            while elapsed < max_wait:
                time.sleep(poll_interval)
                elapsed += poll_interval

                call_detail = self.client.call.retrieve(call_id)
                if call_detail.call_status in ["ended", "error"]:
                    break

            # Get call details
            call_detail = self.client.call.retrieve(call_id)

            if call_detail.call_status == "error":
                result.status = TestStatus.FAILED
                result.summary = f"Call failed: {call_detail.disconnection_reason}"
                return result

            # Get transcript
            transcript = call_detail.transcript or ""
            result.inbound_content = transcript
            result.completed_at = datetime.now()
            result.response_time_seconds = (
                call_detail.start_timestamp and call_detail.end_timestamp
                and (call_detail.end_timestamp - call_detail.start_timestamp) / 1000
            ) or 0

            print(f"📝 Call completed. Duration: {result.response_time_seconds:.0f}s")

            return result

        except Exception as e:
            result.status = TestStatus.FAILED
            result.summary = f"Call failed: {str(e)}"
            return result

    def score_call(self, result: ChannelResult, criteria: list[dict]) -> ChannelResult:
        """Score the phone call interaction."""
        if not result.inbound_content:
            result.status = TestStatus.FAILED
            result.summary = "No transcript available to score."
            return result

        scoring = score_interaction(
            channel="phone call",
            criteria=criteria,
            outbound_content=result.outbound_content,
            inbound_content=result.inbound_content,
            response_time_seconds=result.response_time_seconds,
            context="This is a transcript of a phone call between an AI mystery shopper and a hotel front desk.",
        )

        result.scores = scoring["scores"]
        result.overall_score = scoring["overall_score"]
        result.summary = scoring["summary"]
        result.strengths = scoring["strengths"]
        result.improvements = scoring["improvements"]
        result.status = TestStatus.COMPLETED

        return result


def run_phone_test(
    phone_number: str,
    target_name: str = "Hotel",
    persona_index: int = 0,
) -> ChannelResult:
    """Run a complete phone mystery shopping test."""
    scenario = get_phone_scenario(persona_index)
    shopper = PhoneMysteryShopper()

    # Make the call
    result = shopper.make_call(phone_number, scenario)

    if result.status == TestStatus.FAILED:
        return result

    # Score it
    return shopper.score_call(result, scenario["scoring_criteria"])

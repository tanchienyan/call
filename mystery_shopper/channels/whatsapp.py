"""WhatsApp channel — send and receive WhatsApp messages via wacli."""

import subprocess
import json
import time
from datetime import datetime
from ..orchestrator.journey import StepResult, StepStatus, JourneyStep


def _run_wacli(args: list[str]) -> tuple[int, str]:
    """Run a wacli command and return (returncode, output)."""
    try:
        result = subprocess.run(
            ["wacli"] + args,
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode, result.stdout + result.stderr
    except FileNotFoundError:
        return -1, "wacli not installed. Install with: brew install steipete/tap/wacli"
    except Exception as e:
        return -1, str(e)


async def send_whatsapp(step: JourneyStep, context: dict) -> StepResult:
    """Send a WhatsApp message to the target."""
    result = StepResult(
        step_name=step.name,
        step_type=step.step_type,
        started_at=datetime.now(),
    )

    to = step.config.get("to", "")
    message = step.config.get("message", "")

    if not to or not message:
        result.status = StepStatus.FAILED
        result.notes = "Missing 'to' or 'message' in config"
        return result

    # Inject context into message if needed
    persona = context.get("persona", {})
    message = message.replace("{persona_name}", persona.get("name", "Sarah"))

    print(f"   📱 Sending WhatsApp to {to}...")
    print(f"   💬 Message: {message[:100]}...")

    code, output = _run_wacli(["send", "text", "--to", to, "--message", message])

    if code == 0:
        result.status = StepStatus.COMPLETED
        result.data_sent = message
        result.notes = f"WhatsApp sent successfully to {to}"
        print(f"   ✅ Sent!")
    elif code == -1 and "not installed" in output:
        result.status = StepStatus.FAILED
        result.notes = output
        print(f"   ⚠️  {output}")
    else:
        result.status = StepStatus.FAILED
        result.notes = f"wacli error: {output}"
        print(f"   ❌ Failed: {output[:100]}")

    result.completed_at = datetime.now()
    return result


async def wait_whatsapp(step: JourneyStep, context: dict) -> StepResult:
    """Wait for a WhatsApp reply from the target."""
    result = StepResult(
        step_name=step.name,
        step_type=step.step_type,
        started_at=datetime.now(),
    )

    from_number = step.config.get("from", "")
    timeout_hours = step.config.get("timeout_hours", 24)
    check_interval = step.config.get("check_interval_minutes", 30)

    print(f"   📲 Waiting for WhatsApp reply from {from_number}...")
    print(f"   ⏰ Timeout: {timeout_hours} hours")

    start_time = time.time()
    timeout_seconds = timeout_hours * 3600
    check_count = 0

    while time.time() - start_time < timeout_seconds:
        check_count += 1

        # Search for recent messages from this number
        code, output = _run_wacli([
            "messages", "search", "",
            "--chat", from_number.replace("+", "") + "@s.whatsapp.net",
            "--limit", "5", "--json",
        ])

        if code == 0 and output.strip():
            try:
                messages = json.loads(output)
                # Check if any message is newer than our start time
                for msg in messages:
                    msg_time = msg.get("timestamp", 0)
                    if msg_time > start_time:
                        reply_text = msg.get("text", msg.get("body", ""))
                        result.status = StepStatus.COMPLETED
                        result.data_received = reply_text
                        result.response_time_seconds = time.time() - start_time
                        result.completed_at = datetime.now()
                        hours = result.response_time_seconds / 3600
                        result.notes = f"Reply received after {hours:.1f} hours"
                        print(f"   ✅ Reply received after {hours:.1f}h: {reply_text[:100]}")
                        return result
            except json.JSONDecodeError:
                pass

        if check_count == 1:
            print(f"   ⏳ No reply yet. Checking every {check_interval} minutes...")

        time.sleep(check_interval * 60)

    # Timeout
    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.response_time_seconds = timeout_seconds
    result.notes = f"No WhatsApp reply received within {timeout_hours} hours"
    result.scores = {"overall": 0}
    print(f"   ❌ No reply after {timeout_hours} hours")

    return result

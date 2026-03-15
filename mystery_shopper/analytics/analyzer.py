"""Full journey analyzer — scores the entire customer experience across all channels."""

import json
from openai import OpenAI
from ..config import config


def analyze_full_journey(journey_report: dict) -> dict:
    """Analyze the complete journey using LLM and produce a comprehensive scorecard."""

    steps_summary = ""
    for step in journey_report.get("steps", []):
        steps_summary += f"\n### {step['step_name']} ({step['step_type']})\n"
        steps_summary += f"Status: {step['status']}\n"
        if step.get("response_time_seconds"):
            hours = step["response_time_seconds"] / 3600
            if hours >= 1:
                steps_summary += f"Response time: {hours:.1f} hours\n"
            else:
                steps_summary += f"Response time: {step['response_time_seconds']:.0f} seconds\n"
        if step.get("data_sent"):
            steps_summary += f"Sent: {step['data_sent'][:300]}\n"
        if step.get("data_received"):
            steps_summary += f"Received: {step['data_received'][:300]}\n"
        if step.get("notes"):
            steps_summary += f"Notes: {step['notes']}\n"

    prompt = f"""You are an expert mystery shopping analyst. Analyze this complete customer journey
and produce a comprehensive assessment.

## Journey Data
{steps_summary}

## Score these dimensions (0-100 each):

1. **First Impression** - Website quality, ease of finding info, professionalism
2. **Response Speed** - How fast did they respond across all channels?
3. **Personalization** - Did they tailor responses to the customer's needs?
4. **Cross-Channel Consistency** - Did info match across website/chat/email/phone?
5. **Product Knowledge** - Did staff know their rooms, rates, amenities?
6. **Proactive Service** - Did they upsell, suggest extras, anticipate needs?
7. **Follow-up** - Did they chase the customer proactively?
8. **Booking Conversion** - How effectively did they try to convert the inquiry?
9. **Overall Hospitality** - The feeling of being welcomed and valued

Return JSON:
{{
    "dimensions": [
        {{"name": "First Impression", "score": 0-100, "notes": "..."}},
        ...
    ],
    "overall_score": 0-100,
    "executive_summary": "2-3 sentence summary for the hotel GM",
    "top_strengths": ["...", "..."],
    "critical_improvements": ["...", "..."],
    "revenue_impact": "Estimate how these issues affect revenue (e.g., 'Slow email response likely loses 20-30% of email inquiries')",
    "competitive_benchmark": "How this compares to industry average (poor/below average/average/above average/excellent)",
    "quick_wins": ["Things they could fix immediately for instant improvement"]
}}

Return ONLY valid JSON."""

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def generate_journey_html_report(journey_report: dict, analysis: dict, target_name: str) -> str:
    """Generate a beautiful HTML report for the full journey."""
    overall = analysis.get("overall_score", 0)
    score_color = "#22c55e" if overall >= 80 else "#eab308" if overall >= 60 else "#f97316" if overall >= 40 else "#ef4444"

    # Dimensions
    dims_html = ""
    for dim in analysis.get("dimensions", []):
        d_score = dim.get("score", 0)
        d_color = "#22c55e" if d_score >= 80 else "#eab308" if d_score >= 60 else "#f97316" if d_score >= 40 else "#ef4444"
        dims_html += f"""
        <div class="dim-row">
            <div class="dim-name">{dim['name']}</div>
            <div class="dim-bar-bg"><div class="dim-bar" style="width:{d_score}%;background:{d_color}"></div></div>
            <div class="dim-score" style="color:{d_color}">{d_score}</div>
        </div>
        <div class="dim-notes">{dim.get('notes', '')}</div>"""

    # Journey timeline
    timeline_html = ""
    step_icons = {
        "browse_website": "🌐", "webchat": "💬", "send_email": "📧",
        "wait_email": "📨", "phone_call": "📞", "send_whatsapp": "📱",
        "wait_whatsapp": "📲", "wait_followup": "⏳", "analyze": "📊",
    }
    for i, step in enumerate(journey_report.get("steps", [])):
        icon = step_icons.get(step["step_type"], "📋")
        status_class = "completed" if step["status"] == "completed" else "failed" if step["status"] == "failed" else "skipped"
        time_info = ""
        if step.get("response_time_seconds"):
            h = step["response_time_seconds"] / 3600
            time_info = f"{h:.1f}h" if h >= 1 else f"{step['response_time_seconds']:.0f}s"

        timeline_html += f"""
        <div class="timeline-item {status_class}">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <div class="timeline-header">
                    <span class="timeline-icon">{icon}</span>
                    <span class="timeline-name">{step['step_name']}</span>
                    <span class="timeline-time">{time_info}</span>
                </div>
                <div class="timeline-notes">{step.get('notes', '')}</div>
            </div>
        </div>"""

    strengths = "".join(f"<li>{s}</li>" for s in analysis.get("top_strengths", []))
    improvements = "".join(f"<li>{s}</li>" for s in analysis.get("critical_improvements", []))
    quick_wins = "".join(f"<li>{s}</li>" for s in analysis.get("quick_wins", []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Journey Report — {target_name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;padding:2rem}}
.container{{max-width:850px;margin:0 auto}}
.header{{text-align:center;padding:2rem 0}}
.header h1{{color:#94a3b8;font-size:1.2rem;margin-bottom:.5rem}}
.header h2{{font-size:2rem;color:#f8fafc}}
.score-circle{{display:inline-flex;align-items:center;justify-content:center;width:140px;height:140px;border-radius:50%;font-size:3.5rem;font-weight:bold;color:white;background:{score_color};box-shadow:0 0 40px {score_color}40;margin:1.5rem 0}}
.benchmark{{color:#94a3b8;font-size:1.1rem;margin:.5rem 0}}
.summary{{background:#1e293b;border-radius:12px;padding:1.5rem;margin:1.5rem 0;line-height:1.6}}
.section{{background:#1e293b;border-radius:12px;padding:1.5rem;margin:1rem 0}}
.section h3{{margin-bottom:1rem;font-size:1.1rem}}
.dim-row{{display:flex;align-items:center;gap:.75rem;margin-bottom:.25rem}}
.dim-name{{width:200px;font-size:.9rem}}
.dim-bar-bg{{flex:1;height:8px;background:#334155;border-radius:4px}}
.dim-bar{{height:100%;border-radius:4px;transition:width .5s}}
.dim-score{{width:35px;text-align:right;font-weight:bold}}
.dim-notes{{font-size:.8rem;color:#64748b;margin:0 0 .75rem 200px;padding-left:.75rem}}
.timeline-item{{display:flex;gap:1rem;padding:.75rem 0;border-left:2px solid #334155;margin-left:1rem;padding-left:1.5rem;position:relative}}
.timeline-item.completed{{border-color:#22c55e}}
.timeline-item.failed{{border-color:#ef4444}}
.timeline-item.skipped{{border-color:#64748b}}
.timeline-dot{{position:absolute;left:-6px;top:1rem;width:10px;height:10px;border-radius:50%;background:#334155}}
.timeline-item.completed .timeline-dot{{background:#22c55e}}
.timeline-item.failed .timeline-dot{{background:#ef4444}}
.timeline-header{{display:flex;gap:.5rem;align-items:center}}
.timeline-icon{{font-size:1.2rem}}
.timeline-name{{font-weight:600}}
.timeline-time{{color:#94a3b8;font-size:.85rem;margin-left:auto}}
.timeline-notes{{font-size:.85rem;color:#94a3b8;margin-top:.25rem}}
ul{{padding-left:1.5rem}}li{{margin:.3rem 0;color:#cbd5e1}}
.revenue{{background:#1e293b;border-left:3px solid #f97316;border-radius:0 12px 12px 0;padding:1.5rem;margin:1rem 0}}
.footer{{text-align:center;color:#475569;margin-top:2rem}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>🕵️ AI Mystery Shopper — Full Journey Report</h1>
<h2>{target_name}</h2>
<div class="score-circle">{overall}</div>
<div class="benchmark">Competitive Benchmark: <strong>{analysis.get('competitive_benchmark', 'N/A')}</strong></div>
</div>

<div class="summary">
<h3>📝 Executive Summary</h3>
<p style="margin-top:.5rem">{analysis.get('executive_summary', '')}</p>
</div>

<div class="section">
<h3>📊 Performance Dimensions</h3>
{dims_html}
</div>

<div class="section">
<h3>🗺️ Customer Journey Timeline</h3>
{timeline_html}
</div>

<div class="section" style="display:flex;gap:1rem">
<div style="flex:1"><h3>💪 Strengths</h3><ul>{strengths}</ul></div>
<div style="flex:1"><h3>🔧 Critical Improvements</h3><ul>{improvements}</ul></div>
</div>

<div class="revenue">
<h3>💰 Revenue Impact</h3>
<p style="margin-top:.5rem">{analysis.get('revenue_impact', '')}</p>
</div>

<div class="section">
<h3>⚡ Quick Wins</h3>
<ul>{quick_wins}</ul>
</div>

<div class="footer"><p>Generated by AI Mystery Shopper · Confidential</p></div>
</div>
</body>
</html>"""

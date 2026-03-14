"""Web dashboard for AI Mystery Shopper."""

import json
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from .config import config
from .demo import run_demo

app = FastAPI(title="AI Mystery Shopper", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main dashboard page."""
    # Load existing reports
    reports = []
    data_dir = config.DATA_DIR
    if data_dir.exists():
        for f in sorted(data_dir.glob("*.json"), reverse=True):
            try:
                with open(f) as fh:
                    report = json.load(fh)
                    reports.append(report)
            except Exception:
                pass

    reports_html = ""
    for r in reports[:20]:
        score = r.get("overall_score", 0)
        color = "#22c55e" if score >= 80 else "#eab308" if score >= 60 else "#f97316" if score >= 40 else "#ef4444"
        channels_badges = ""
        for ch_name, ch_data in r.get("channels", {}).items():
            ch_score = ch_data.get("overall_score", 0)
            ch_color = "#22c55e" if ch_score >= 80 else "#eab308" if ch_score >= 60 else "#f97316" if ch_score >= 40 else "#ef4444"
            icon = {"email": "📧", "phone": "📞", "webchat": "💬"}.get(ch_name, "📋")
            channels_badges += f'<span class="ch-badge" style="border-color:{ch_color}">{icon} {ch_score}</span>'

        report_id = r.get("id", "unknown")
        reports_html += f"""
        <div class="report-row" onclick="window.location='/report/{report_id}'">
            <div class="report-score" style="background:{color}">{score}</div>
            <div class="report-info">
                <div class="report-name">{r.get('target', {}).get('name', 'Unknown')}</div>
                <div class="report-date">{r.get('created_at', '')[:16]}</div>
            </div>
            <div class="report-channels">{channels_badges}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Mystery Shopper</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }}
        .nav {{ background: #1e293b; padding: 1rem 2rem; display: flex; align-items: center; gap: 1rem; border-bottom: 1px solid #334155; }}
        .nav h1 {{ font-size: 1.3rem; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 2rem; }}

        .hero {{ text-align: center; padding: 3rem 0; }}
        .hero h2 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        .hero p {{ color: #94a3b8; font-size: 1.1rem; }}

        .actions {{ display: flex; gap: 1rem; justify-content: center; margin: 2rem 0; flex-wrap: wrap; }}
        .btn {{ padding: 0.75rem 1.5rem; border-radius: 8px; border: none; font-size: 1rem; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 0.5rem; }}
        .btn-primary {{ background: #3b82f6; color: white; }}
        .btn-primary:hover {{ background: #2563eb; }}
        .btn-secondary {{ background: #334155; color: #e2e8f0; }}
        .btn-secondary:hover {{ background: #475569; }}

        .demo-form {{ background: #1e293b; padding: 2rem; border-radius: 12px; margin: 2rem 0; }}
        .demo-form h3 {{ margin-bottom: 1rem; }}
        .form-row {{ display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }}
        .form-group {{ flex: 1; min-width: 200px; }}
        .form-group label {{ display: block; margin-bottom: 0.25rem; color: #94a3b8; font-size: 0.9rem; }}
        .form-group input, .form-group select {{ width: 100%; padding: 0.5rem; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #e2e8f0; font-size: 1rem; }}

        .reports {{ margin-top: 2rem; }}
        .reports h3 {{ margin-bottom: 1rem; }}
        .report-row {{ display: flex; align-items: center; gap: 1rem; padding: 1rem; background: #1e293b; border-radius: 8px; margin-bottom: 0.5rem; cursor: pointer; transition: background 0.2s; }}
        .report-row:hover {{ background: #334155; }}
        .report-score {{ width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 0.95rem; flex-shrink: 0; }}
        .report-info {{ flex: 1; }}
        .report-name {{ font-weight: 600; }}
        .report-date {{ color: #64748b; font-size: 0.85rem; }}
        .report-channels {{ display: flex; gap: 0.5rem; }}
        .ch-badge {{ padding: 0.2rem 0.5rem; border-radius: 4px; border: 1px solid; font-size: 0.85rem; }}
        .empty {{ text-align: center; color: #64748b; padding: 3rem; }}

        #result {{ margin-top: 1rem; }}
    </style>
</head>
<body>
    <nav class="nav">
        <h1>🕵️ AI Mystery Shopper</h1>
    </nav>

    <div class="container">
        <div class="hero">
            <h2>Test Your Service Quality</h2>
            <p>AI-powered omnichannel mystery shopping for hotels & service businesses</p>
        </div>

        <div class="demo-form">
            <h3>🚀 Run a Demo Test</h3>
            <form id="demoForm">
                <div class="form-row">
                    <div class="form-group">
                        <label>Hotel Name</label>
                        <input type="text" name="target" value="The Grand Hotel" />
                    </div>
                    <div class="form-group">
                        <label>Simulated Quality</label>
                        <select name="quality">
                            <option value="good">Good — Fast, professional, proactive</option>
                            <option value="average" selected>Average — Functional but uninspired</option>
                            <option value="poor">Poor — Slow, disengaged, unhelpful</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Channels</label>
                        <select name="channels">
                            <option value="email,phone">📧 Email + 📞 Phone</option>
                            <option value="email">📧 Email only</option>
                            <option value="phone">📞 Phone only</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary">🕵️ Run Mystery Shop</button>
            </form>
            <div id="result"></div>
        </div>

        <div class="reports">
            <h3>📋 Recent Reports</h3>
            {reports_html if reports_html else '<div class="empty">No reports yet. Run a demo to get started!</div>'}
        </div>
    </div>

    <script>
        document.getElementById('demoForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const form = new FormData(e.target);
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = '<p style="color:#94a3b8">🔄 Running mystery shop...</p>';

            try {{
                const resp = await fetch('/api/demo', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        target: form.get('target'),
                        quality: form.get('quality'),
                        channels: form.get('channels'),
                    }}),
                }});
                const data = await resp.json();
                resultDiv.innerHTML = `
                    <p style="color:#22c55e;margin-top:1rem">✅ Done! Overall score: <strong>${{data.overall_score}}/100</strong></p>
                    <a href="/report/${{data.id}}" class="btn btn-secondary" style="margin-top:0.5rem">View Full Report →</a>
                `;
                setTimeout(() => location.reload(), 500);
            }} catch (err) {{
                resultDiv.innerHTML = `<p style="color:#ef4444">❌ Error: ${{err.message}}</p>`;
            }}
        }});
    </script>
</body>
</html>"""


@app.post("/api/demo")
async def api_demo(request: Request):
    """Run a demo mystery shopping session."""
    body = await request.json()
    channels = [c.strip() for c in body.get("channels", "email,phone").split(",")]

    session = run_demo(
        target_name=body.get("target", "The Grand Hotel"),
        quality=body.get("quality", "average"),
        channels=channels,
    )

    return JSONResponse(session.to_dict())


@app.get("/report/{report_id}", response_class=HTMLResponse)
async def view_report(report_id: str):
    """View an HTML report."""
    html_path = config.DATA_DIR / f"report_{report_id}.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text())

    # Try to find and regenerate from JSON
    json_path = config.DATA_DIR / f"report_{report_id}.json"
    if json_path.exists():
        with open(json_path) as f:
            data = json.load(f)
        # Return a simple JSON view
        return HTMLResponse(f"<pre>{json.dumps(data, indent=2)}</pre>")

    return HTMLResponse("<h1>Report not found</h1>", status_code=404)


@app.get("/api/reports")
async def list_reports():
    """List all reports."""
    reports = []
    if config.DATA_DIR.exists():
        for f in sorted(config.DATA_DIR.glob("*.json"), reverse=True):
            try:
                with open(f) as fh:
                    reports.append(json.load(fh))
            except Exception:
                pass
    return JSONResponse(reports[:50])

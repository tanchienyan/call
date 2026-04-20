"""Tiny local proxy for the legacy Retell browser-SDK demo.

NOTE: This predates the self-hosted ai_caller/ pipeline. Kept as a
reference only. Do NOT hardcode API keys here; read from env.
"""
import json
import os
import ssl
import sys
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("RETELL_API_KEY", "")
AGENT_ID = os.getenv("RETELL_AGENT_ID", "")

if not API_KEY or not AGENT_ID:
    sys.stderr.write(
        "ERROR: RETELL_API_KEY and RETELL_AGENT_ID must be set in the environment.\n"
        "Copy .env.example to .env and fill in the values, or export them directly.\n"
    )
    sys.exit(1)


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/create-call":
            req = urllib.request.Request(
                "https://api.retellai.com/v2/create-web-call",
                data=json.dumps({"agent_id": AGENT_ID}).encode(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
                method="POST",
            )
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx) as resp:
                body = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


if __name__ == "__main__":
    print("Server running at http://localhost:8877")
    HTTPServer(("localhost", 8877), Handler).serve_forever()

"""Tiny server for web call testing."""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json, urllib.request, ssl

API_KEY = "key_172f6e7584a1116764d25f88a352"
AGENT_ID = "agent_a8ede5afc28f6ed16682a94e75"

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

print("Server running at http://localhost:8877")
HTTPServer(("localhost", 8877), Handler).serve_forever()

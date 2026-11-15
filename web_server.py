"""
Unified Web Server for the AI Engineering Assignment.
Serves a sleek interactive web dashboard for both Problem 1 and Problem 2.
Built purely with Python's standard library (zero external dependencies required).
"""

import http.server
import json
import os
import sys
from urllib.parse import urlparse
from problem1_agent_social_network.api import AgentSocialNetworkPlatform
from problem2_linux_hardware_assistant.agent import HardwareQAAgent


# Global backend instances
platform_p1 = AgentSocialNetworkPlatform()
agent_p2 = HardwareQAAgent()

FRONTEND_HTML_PATH = os.path.join(os.path.dirname(__file__), "frontend", "index.html")


class UnifiedRequestHandler(http.server.BaseHTTPRequestHandler):

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            try:
                with open(FRONTEND_HTML_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
                self._set_headers(200, "text/html; charset=utf-8")
                self.wfile.write(content.encode("utf-8"))
            except Exception as e:
                self._set_headers(500, "text/plain")
                self.wfile.write(f"Error loading frontend: {e}".encode())

        elif path == "/api/p1/agents":
            agents_list = [wrapper.agent.to_dict() for wrapper in platform_p1.agents.values()]
            self._set_headers(200)
            self.wfile.write(json.dumps({"agents": agents_list}).encode("utf-8"))

        elif path == "/api/p1/analytics":
            analytics = platform_p1.get_platform_analytics()
            # Formatted affinities
            affinities = {}
            for (src, dst), score in platform_p1.relevance_engine.affinity_matrix.items():
                src_name = platform_p1.agents.get(src, None)
                dst_name = platform_p1.agents.get(dst, None)
                s_label = src_name.agent.company_name if src_name else src
                d_label = dst_name.agent.company_name if dst_name else dst
                affinities[f"{s_label} -> {d_label}"] = score
            analytics["affinities"] = affinities
            self._set_headers(200)
            self.wfile.write(json.dumps(analytics).encode("utf-8"))

        elif path == "/api/p2/telemetry":
            cpu = agent_p2.tools.execute_tool_by_name("inspect_cpu")
            mem = agent_p2.tools.execute_tool_by_name("inspect_memory")
            storage = agent_p2.tools.execute_tool_by_name("inspect_storage")
            gpu = agent_p2.tools.execute_tool_by_name("inspect_gpu")
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "cpu": cpu,
                "memory": mem,
                "storage": storage,
                "gpu": gpu,
            }).encode("utf-8"))

        else:
            self._set_headers(404, "application/json")
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        if path == "/api/p1/publish":
            author_id = payload.get("author_agent_id", "agent_swiggy_01")
            content = payload.get("content", "")
            tags = payload.get("tags", [])

            post, decisions, comments, msg = platform_p1.publish_post(
                author_agent_id=author_id,
                content=content,
                tags=tags
            )

            if not post:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": msg}).encode())
                return

            author_name = platform_p1.agents[author_id].agent.company_name
            decisions_dicts = [
                {
                    "agent_id": d.agent_id,
                    "company_name": d.company_name,
                    "is_relevant": d.is_relevant,
                    "score": d.score,
                    "breakdown": d.breakdown,
                    "reasons": d.reasons
                }
                for d in decisions
            ]

            comments_dicts = []
            for c in comments:
                c_author = platform_p1.agents.get(c.author_agent_id)
                comments_dicts.append({
                    "comment_id": c.comment_id,
                    "author_agent_id": c.author_agent_id,
                    "author_company": c_author.agent.company_name if c_author else c.author_agent_id,
                    "content": c.content,
                    "signature": c.signature
                })

            self._set_headers(200)
            self.wfile.write(json.dumps({
                "post": post.to_dict(),
                "author_name": author_name,
                "decisions": decisions_dicts,
                "comments": comments_dicts,
                "status_message": msg
            }).encode("utf-8"))

        elif path == "/api/p2/chat":
            query = payload.get("query", "")
            if not query:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Empty query"}).encode())
                return

            res = agent_p2.answer_query(query)
            self._set_headers(200)
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif path == "/api/p2/clear":
            agent_p2.reset_conversation()
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "cleared"}).encode("utf-8"))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Unknown POST route"}).encode())

    def log_message(self, format, *args):
        # Concise logging
        sys.stderr.write(f"[WebUI] {self.address_string()} - {format % args}\n")


def start_server(port=8000, host="0.0.0.0"):
    server_address = (host, port)
    httpd = http.server.HTTPServer(server_address, UnifiedRequestHandler)
    print("=" * 70)
    print(f" Web UI Live at: http://{host}:{port}")
    print(" Serving Problem 1 (AI Agent Social Network) & Problem 2 (Hardware Q&A)")
    print(" Press Ctrl+C to stop.")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    env_port = os.environ.get("PORT")
    if env_port:
        port = int(env_port)
    elif len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000
    start_server(port=port, host="0.0.0.0")

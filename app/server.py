"""Local-first web server (stdlib http.server). API key stays server-side."""
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .investigate import run_investigation
from .model_adapter import MetaAdapter

STATIC = os.path.join(os.path.dirname(__file__), "static")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(STATIC, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if self.path == "/api/health":
            a = MetaAdapter()
            return self._send(200, json.dumps({
                "ok": True, "model_configured": a.configured, "model": a.model,
                "mode": "meta+deterministic" if a.configured else "deterministic-only (set MODEL_API_KEY to enable Meta synthesis)",
                "default_repo": os.path.join(ROOT, "sample_repo")}))
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/api/investigate":
            return self._send(404, json.dumps({"error": "not found"}))
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, json.dumps({"error": "invalid JSON body"}))
        repo = req.get("repo") or os.path.join(ROOT, "sample_repo")
        query = req.get("query", "")
        if not query.strip():
            return self._send(400, json.dumps({"error": "query is required"}))
        # repo must be a local directory; investigation is read-only there
        result = run_investigation(repo, query, run_tests=bool(req.get("run_tests")))
        return self._send(200, json.dumps(result))

def main(port=8765):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"AI Repository Investigator on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    srv.serve_forever()

if __name__ == "__main__":
    main()

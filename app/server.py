"""Local-first web server (stdlib http.server). API key stays server-side.

Security model (see docs/review-findings.md H2):
- Binds 127.0.0.1 only. Investigation is read-only for any existing local dir
  (optionally confined by INVESTIGATOR_ALLOWED_ROOTS, os.pathsep-separated).
- Test execution RUNS repository code with the user's privileges and is NOT
  sandboxed. It therefore requires an explicit per-request confirmation
  (test_execution_confirmed=true, set by the UI only after a confirm dialog)
  and can be disabled outright with INVESTIGATOR_DISABLE_TEST_EXECUTION=1.
"""
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .investigate import run_investigation
from .model_adapter import MetaAdapter

STATIC = os.path.join(os.path.dirname(__file__), "static")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_dotenv():
    """Load KEY=VALUE pairs from a project-root .env into the process env
    (existing environment wins). Values are never logged. .env is gitignored."""
    path = os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
MAX_QUERY_CHARS = 20_000

def validate_investigate_request(req):
    """Return (repo, query, run_tests, error). error is None on success."""
    if not isinstance(req, dict):
        return None, None, False, "JSON object body required"
    repo_raw = req.get("repo") or os.path.join(ROOT, "sample_repo")
    if not isinstance(repo_raw, str):
        return None, None, False, "repo must be a string path"
    repo = os.path.realpath(os.path.expanduser(repo_raw))
    if not os.path.isdir(repo):
        return None, None, False, f"repository path is not an existing directory: {repo_raw}"
    allowed = os.environ.get("INVESTIGATOR_ALLOWED_ROOTS", "")
    if allowed:
        roots = [os.path.realpath(r) for r in allowed.split(os.pathsep) if r]
        if not any(repo == r or repo.startswith(r + os.sep) for r in roots):
            return None, None, False, "repository path is outside INVESTIGATOR_ALLOWED_ROOTS"
    query = req.get("query", "")
    if not isinstance(query, str) or not query.strip():
        return None, None, False, "query is required"
    if len(query) > MAX_QUERY_CHARS:
        return None, None, False, f"query exceeds {MAX_QUERY_CHARS} characters"
    run_tests = bool(req.get("run_tests"))
    if run_tests:
        if os.environ.get("INVESTIGATOR_DISABLE_TEST_EXECUTION") == "1":
            return None, None, False, "test execution is disabled by INVESTIGATOR_DISABLE_TEST_EXECUTION=1"
        if req.get("test_execution_confirmed") is not True:
            return None, None, False, (
                "test execution runs repository code with your privileges and is not sandboxed; "
                "it requires explicit confirmation (test_execution_confirmed=true)")
    return repo, query, run_tests, None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
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
                "test_execution_disabled": os.environ.get("INVESTIGATOR_DISABLE_TEST_EXECUTION") == "1",
                "default_repo": os.path.join(ROOT, "demo_webapp")}))
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/api/investigate":
            return self._send(404, json.dumps({"error": "not found"}))
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 10_000_000:  # accommodates a <=5MB screenshot as base64
                return self._send(413, json.dumps({"error": "request body too large"}))
            req = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, json.dumps({"error": "invalid JSON body"}))
        repo, query, run_tests, error = validate_investigate_request(req)
        if error:
            return self._send(400, json.dumps({"error": error}))
        screenshot = None
        if req.get("screenshot_b64"):
            from .visual import decode_image, ImageError
            try:
                screenshot = decode_image(req["screenshot_b64"])
            except ImageError as e:
                return self._send(400, json.dumps({"error": f"screenshot rejected: {e}"}))
        for fld in ("console_log", "network_log"):
            if req.get(fld) is not None and not isinstance(req.get(fld), str):
                return self._send(400, json.dumps({"error": f"{fld} must be a string"}))
            if req.get(fld) and len(req[fld]) > 20_000:
                return self._send(400, json.dumps({"error": f"{fld} exceeds 20000 characters"}))
        result = run_investigation(repo, query, run_tests=run_tests, screenshot=screenshot,
                                   console_text=req.get("console_log", ""),
                                   network_text=req.get("network_log", ""))
        return self._send(200, json.dumps(result))

def main(port=8765):
    load_dotenv()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"AI Repository Investigator on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    srv.serve_forever()

if __name__ == "__main__":
    main()

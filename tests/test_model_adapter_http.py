"""Adapter HTTP-path tests against a local stub of the documented Meta
Responses API (review M5). This is NOT a live Meta API test: no real key,
no network beyond 127.0.0.1, no spend."""
import json, os, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.model_adapter import MetaAdapter, ModelError

RESPONSES = []  # queue of (status, payload, headers)

class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def do_POST(self):
        assert self.path == "/v1/responses"
        assert self.headers.get("Authorization") == "Bearer TESTKEY"
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert body["model"] == "muse-spark-1.3" and "input" in body
        status, payload, headers = RESPONSES.pop(0)
        data = json.dumps(payload).encode()
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

def _adapter():
    srv = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return MetaAdapter(api_key="TESTKEY", base_url=f"http://127.0.0.1:{srv.server_address[1]}/v1")

OK = {"id": "r1", "model": "muse-spark-1.3",
      "output": [{"type": "message", "content": [{"type": "output_text", "text": "hello"}]}],
      "usage": {"input_tokens": 1000, "output_tokens": 500}}

def test_http_success_parses_responses_shape_and_cost():
    RESPONSES.append((200, OK, {}))
    a = _adapter()
    assert a.complete("hi") == "hello"
    e = a.ledger[0]
    assert e["input_tokens"] == 1000 and e["output_tokens"] == 500
    assert e["est_cost_usd"] == a.est_cost("muse-spark-1.3", 1000, 500)

def test_http_429_retries_then_succeeds():
    RESPONSES.extend([(429, {"error": "rate"}, {"Retry-After": "0.05"}), (200, OK, {})])
    a = _adapter()
    assert a.complete("hi") == "hello"
    assert len(a.ledger) == 1

def test_http_500_raises_model_error():
    RESPONSES.append((500, {"error": "boom"}, {}))
    a = _adapter()
    try:
        a.complete("hi"); raise AssertionError("expected ModelError")
    except ModelError as e:
        assert "500" in str(e)

def test_malformed_response_raises():
    RESPONSES.append((200, {"output": []}, {}))
    a = _adapter()
    try:
        a.complete("hi"); raise AssertionError("expected ModelError")
    except ModelError:
        pass

def test_unknown_pricing_blocks_subsequent_calls():
    bad = dict(OK); bad["model"] = "some-unpriced-model"
    RESPONSES.extend([(200, bad, {}), (200, OK, {})])
    a = _adapter()
    a.complete("hi")  # succeeds, but cost is unknown
    assert a.ledger[0]["est_cost_usd"] is None
    try:
        a.complete("again"); raise AssertionError("budget must block unknown-cost spend")
    except ModelError:
        pass

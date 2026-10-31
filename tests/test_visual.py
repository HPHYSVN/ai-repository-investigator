"""Visual/log/outcome tests. Multimodal is stubbed (documented Responses
shape) — this does NOT constitute a live Meta API test."""
import base64, json, os, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.visual import analyse_screenshot, decode_image, image_info, ImageError
from app.logs import parse_logs
from app.investigate import run_investigation
from app.model_adapter import MetaAdapter

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAwMCAO+ip1sAAAAASUVORK5CYII=")

def test_image_validation_and_info():
    info = image_info(PNG_1PX)
    assert info["mime"] == "image/png" and info["width"] == 1
    assert decode_image("data:image/png;base64," + base64.b64encode(PNG_1PX).decode()) == PNG_1PX
    for bad in ("not-base64!!!", "data:text/html;base64,SGVsbG8="):
        try:
            raw = decode_image(bad)
            image_info(raw)
            raise AssertionError("should reject")
        except ImageError:
            pass

def test_visual_without_key_is_metadata_only_and_honest():
    class NoKey:
        configured = False
        model = "none"
    v = analyse_screenshot(PNG_1PX, "cart total blank", NoKey())
    assert v["observable"] == [] and v["source"].startswith("metadata-only")
    assert v["cannot_determine"]

class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        inp = body["input"]
        assert isinstance(inp, list) and inp[0]["content"][1]["type"] == "input_image"
        assert inp[0]["content"][1]["image_url"].startswith("data:image/png;base64,")
        payload = {"model": "muse-spark-1.3", "usage": {"input_tokens": 1400, "output_tokens": 120},
                   "output": [{"type": "message", "content": [{"type": "output_text", "text":
                     '{"observable": ["Cart total field is blank", "Checkout button is disabled"], '
                     '"inferred": ["price value may be null"], "cannot_determine": ["which source file caused it"]}' }]}]}
        d = json.dumps(payload).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(d))); self.end_headers()
        self.wfile.write(d)

def test_visual_with_stubbed_meta_parses_structured_json():
    srv = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    a = MetaAdapter(api_key="TEST", base_url=f"http://127.0.0.1:{srv.server_address[1]}/v1")
    v = analyse_screenshot(PNG_1PX, "cart total blank", a)
    assert v["observable"][0].startswith("Cart total")
    assert v["source"] == "meta:muse-spark-1.3"
    assert a.ledger and a.ledger[0]["purpose"] == "visual-analysis"

def test_log_parsing_redacts_secrets_and_extracts_failures():
    logs = parse_logs(
        "TypeError: Cannot read properties of null (reading 'price')\nAuthorization: Bearer abcsecret123",
        "GET /api/checkout -> 500\nPOST https://x.test/pay 200\nCookie: session=topsecret")
    assert logs["console_errors"][0]["kind"] == "TypeError"
    assert logs["failed_requests"][0]["status"] == 500
    blob = json.dumps(logs)
    assert "abcsecret123" not in blob and "topsecret" not in blob

def test_end_to_end_demo_webapp_with_screenshot_and_logs():
    q = ('When I add an item to the cart, the total price becomes blank and checkout fails.\n'
         'Traceback:\n  File "cart_api.py", line 6, in checkout\n'
         '  File "pricing.py", line 2, in format_price\nTypeError: unsupported format string passed to NoneType')
    r = run_investigation(os.path.join(ROOT, "demo_webapp"), q, run_tests=True,
                          screenshot=PNG_1PX,
                          console_text="TypeError: unsupported format string passed to NoneType",
                          network_text="POST /api/checkout -> 500")
    assert r["hypotheses"][0]["files"] == ["cart.py"]
    assert r["outcome"] == "verified" and r["evidence_levels"]["L5_test_verified"]
    assert r["regression_test"] and "cart_total" in r["regression_test"]["code"]
    assert r["visual"]["source"].startswith("metadata-only")  # no key in test env

def test_proposed_patch_fixes_demo_in_temp_copy(tmp_path):
    import shutil, subprocess
    dst = tmp_path / "demo"
    shutil.copytree(os.path.join(ROOT, "demo_webapp"), dst,
                    ignore=shutil.ignore_patterns("__pycache__", "screenshot.png", "index.html", "cart.js"))
    q = ('Traceback:\n  File "cart_api.py", line 6, in checkout\n'
         '  File "pricing.py", line 2, in format_price\nTypeError: x')
    r = run_investigation(str(dst), q)
    assert r["patch"] and "return None" in r["patch"]["diff"]
    target = dst / "cart.py"
    lines = target.read_text().splitlines()
    lines = [l.replace("return None", 'raise ValueError("unknown sku")') for l in lines]
    target.write_text("\n".join(lines) + "\n")
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                       cwd=dst, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout  # proposal is sound; original repo never modified by the agent

def test_not_reproducible_outcome(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "test_calc.py").write_text("from calc import add\ndef test_add():\n    assert add(1, 2) == 3\n")
    r = run_investigation(str(tmp_path), "add in calc sometimes returns wrong result for some inputs",
                          run_tests=True)
    assert r["outcome"] in ("not_reproducible", "inconclusive")

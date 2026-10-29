"""Regression tests for review findings H1 (XSS) and H2 (code execution)."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.investigate import run_investigation
from app.server import validate_investigate_request

HTML = open(os.path.join(ROOT, "app/static/index.html")).read()

# ---- H1: XSS via repo filenames in inline handlers ----

def test_frontend_has_no_inline_event_handlers():
    assert 'onclick="' not in HTML and "onclick='" not in HTML, "no inline handler attributes"
    assert "showSource('${" not in HTML

def test_esc_covers_attribute_context():
    # esc() must escape both quote characters, not only & < >
    assert "&quot;" in HTML and "&#39;" in HTML
    assert "data-file=" in HTML and "addEventListener" in HTML
    assert "data-node-index=" in HTML

def test_crafted_filename_cannot_break_out(tmp_path):
    evil = tmp_path / "x');alert(document.domain);#.py"
    evil.write_text("def f():\n    return None\n")
    (tmp_path / "main.py").write_text("import os\nVALUE = 1\n")
    r = run_investigation(str(tmp_path), "f crashes with NoneType in main VALUE")
    # the dangerous name survives only as JSON data, never as markup
    for n in r["graph"]["nodes"]:
        assert "<script" not in n["label"]
    assert "onclick" not in str(r["graph"])

# ---- H2: arbitrary code execution via the localhost API ----

def _hostile_repo(tmp_path):
    repo = tmp_path / "hostile"
    repo.mkdir()
    (repo / "lib.py").write_text("X = 1\n")
    (repo / "test_evil.py").write_text(
        "import pathlib\npathlib.Path(__file__).with_name('PWNED').write_text('ran')\n"
        "def test_ok():\n    assert True\n")
    return repo

def test_unconfirmed_test_execution_is_rejected(tmp_path):
    repo = _hostile_repo(tmp_path)
    _, _, _, err = validate_investigate_request(
        {"repo": str(repo), "query": "crash in lib", "run_tests": True})
    assert err and "explicit confirmation" in err
    assert not (repo / "PWNED").exists()

def test_disabled_test_execution_env_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("INVESTIGATOR_DISABLE_TEST_EXECUTION", "1")
    repo = _hostile_repo(tmp_path)
    _, _, _, err = validate_investigate_request(
        {"repo": str(repo), "query": "x", "run_tests": True, "test_execution_confirmed": True})
    assert err and "disabled" in err

def test_repo_path_validation(tmp_path):
    assert validate_investigate_request({"repo": "/nonexistent-xyz", "query": "x"})[3]
    f = tmp_path / "file.txt"; f.write_text("hi")
    assert validate_investigate_request({"repo": str(f), "query": "x"})[3]  # not a dir
    assert validate_investigate_request({"repo": str(tmp_path), "query": "  "})[3]  # empty query

def test_allowed_roots_confinement(tmp_path, monkeypatch):
    inside = tmp_path / "in"; inside.mkdir()
    outside = tmp_path.parent
    monkeypatch.setenv("INVESTIGATOR_ALLOWED_ROOTS", str(inside))
    assert validate_investigate_request({"repo": str(inside), "query": "x"})[3] is None
    assert validate_investigate_request({"repo": str(outside), "query": "x"})[3]

def test_investigation_without_run_tests_never_executes_repo_code(tmp_path):
    repo = _hostile_repo(tmp_path)
    r = run_investigation(str(repo), "lib X crash TypeError", run_tests=False)
    assert r["test_log"] == []
    assert not (repo / "PWNED").exists()

def test_test_subprocess_env_has_no_api_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "TEST-SECRET-VALUE")
    repo = tmp_path / "envrepo"; repo.mkdir()
    (repo / "mod.py").write_text("def f():\n    return 1\n")
    (repo / "test_env.py").write_text(
        "import os, pathlib\n"
        "def test_env():\n"
        "    pathlib.Path(__file__).with_name('env_seen.txt').write_text(os.environ.get('MODEL_API_KEY', 'ABSENT'))\n")
    r = run_investigation(str(repo), "f in mod crashes", run_tests=True)  # explicit library-level opt-in
    assert r["test_log"], "test should have run at the library level"
    assert (repo / "env_seen.txt").read_text() == "ABSENT"
    assert "TEST-SECRET-VALUE" not in r["test_log"][0]["output"]

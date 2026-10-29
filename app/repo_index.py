"""Deterministic repository indexing: files, symbols, imports, calls, BM25.

Respects .gitignore (simple patterns), excludes secrets/binaries/generated dirs.
Python parsed with ast; other text files indexed lexically only.
"""
import ast, fnmatch, hashlib, math, os, re
from collections import Counter, defaultdict

EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox",
                "dist", "build", ".mypy_cache", ".pytest_cache", "expected"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz",
              ".whl", ".so", ".pyc", ".woff", ".woff2", ".mp4"}
SECRET_NAMES = {".env", "credentials", "id_rsa", "id_ed25519"}
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

def _is_secret(name):
    n = name.lower()
    return n in SECRET_NAMES or n.startswith(".env") or n.endswith((".pem", ".key")) or "secret" in n

def _gitignore_patterns(root):
    pats = []
    p = os.path.join(root, ".gitignore")
    if os.path.isfile(p):
        for line in open(p, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#"):
                pats.append(line)
    return pats

def _ignored(rel, pats):
    parts = rel.split("/")
    for pat in pats:
        base = pat.strip("/")
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat + "*") or \
           any(fnmatch.fnmatch(part, base) for part in parts):
            return True
    return False

class Symbol:
    def __init__(self, name, kind, file, start, end):
        self.name, self.kind, self.file, self.start, self.end = name, kind, file, start, end
        self.calls = []       # callee names called inside this symbol
        self.returns_none = False
        self.implicit_none = False

class FileInfo:
    def __init__(self, rel, abspath):
        self.rel, self.abspath = rel, abspath
        self.lines = open(abspath, encoding="utf-8", errors="replace").read().splitlines()
        self.symbols = []     # Symbol
        self.imports = []     # module strings
        self.tf = Counter(TOKEN_RE.findall("\n".join(self.lines)))
        self.detectors = []   # filled by detectors in investigate.py

class RepoIndex:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.files = {}       # rel -> FileInfo
        self.skipped = 0
        self.symbols = {}     # name -> [Symbol]
        self._build()

    def _build(self):
        pats = _gitignore_patterns(self.root)
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, self.root)
                if _ignored(rel, pats) or _is_secret(fn) or os.path.splitext(fn)[1].lower() in BINARY_EXT:
                    self.skipped += 1
                    continue
                try:
                    if os.path.getsize(full) > 512_000:
                        self.skipped += 1
                        continue
                    fi = FileInfo(rel, full)
                except OSError:
                    self.skipped += 1
                    continue
                self.files[rel] = fi
                if rel.endswith(".py"):
                    self._parse_python(fi)
        # BM25 stats
        self.N = max(len(self.files), 1)
        self.df = Counter()
        for fi in self.files.values():
            for t in fi.tf:
                self.df[t] += 1
        self.avgdl = sum(sum(f.tf.values()) for f in self.files.values()) / self.N or 1

    def _parse_python(self, fi):
        try:
            tree = ast.parse("\n".join(fi.lines))
        except SyntaxError:
            return
        mod_by_stem = {os.path.splitext(os.path.basename(r))[0]: r for r in self.files}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import,)):
                for a in node.names:
                    fi.imports.append(a.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    fi.imports.append(node.module)
        def visit(node, prefix=""):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    kind = "class" if isinstance(child, ast.ClassDef) else "function"
                    sym = Symbol(prefix + child.name, kind, fi.rel,
                                 child.lineno, getattr(child, "end_lineno", child.lineno))
                    if kind == "function":
                        for n in ast.walk(child):
                            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                                # Only plain name calls are resolved into call edges.
                                # Attribute calls (obj.method()) are NOT resolved by
                                # name: doing so produced false edges (e.g. dict.get
                                # -> any function named "get"). See docs/review-findings.md B.
                                sym.calls.append(n.func.id)
                            elif isinstance(n, ast.Return):
                                if isinstance(n.value, ast.Constant) and n.value.value is None:
                                    sym.returns_none = True
                        # implicit None: no non-None return at all
                        rets = [n for n in ast.walk(child) if isinstance(n, ast.Return) and n.value is not None]
                        if not any(not (isinstance(r.value, ast.Constant) and r.value.value is None) for r in rets):
                            sym.implicit_none = True
                    fi.symbols.append(sym)
                    self.symbols.setdefault(child.name, []).append(sym)
                    visit(child, prefix + child.name + ".")
                else:
                    visit(child, prefix)
        visit(tree)

    # ---- retrieval ----
    def bm25_search(self, terms, limit=8):
        terms = [t for t in dict.fromkeys(terms) if t]
        scored = []
        k1, b = 1.5, 0.75
        for rel, fi in self.files.items():
            score = 0.0
            dl = sum(fi.tf.values()) or 1
            for t in terms:
                tf = fi.tf.get(t, 0)
                if not tf:
                    continue
                idf = math.log(1 + (self.N - self.df.get(t, 0) + 0.5) / (self.df.get(t, 0) + 0.5))
                score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / self.avgdl))
            # symbol-name boost: exact symbol match is a strong signal
            for t in terms:
                if any(s.name.split(".")[-1] == t for s in fi.symbols):
                    score += 3.0
            if score > 0:
                scored.append((score, rel))
        scored.sort(reverse=True)
        return scored[:limit]

    def snippet(self, rel, start, end):
        fi = self.files.get(rel)
        if not fi or start < 1 or end > len(fi.lines) or start > end:
            return None
        text = "\n".join(fi.lines[start - 1:end])
        return {"file": rel, "start": start, "end": end, "text": text,
                "sha256": hashlib.sha256(text.encode()).hexdigest()}

    def validate_citation(self, rel, start, end, sha256=None):
        s = self.snippet(rel, start, end)
        if s is None:
            return False
        return sha256 is None or s["sha256"] == sha256

    def file_by_stem(self, stem):
        for rel in self.files:
            if os.path.splitext(os.path.basename(rel))[0] == stem:
                return rel
        return None

    def import_edges(self):
        """file -> [file] from python imports resolved by module stem."""
        edges = []
        for rel, fi in self.files.items():
            for mod in fi.imports:
                target = self.file_by_stem(mod.split(".")[-1])
                if target and target != rel:
                    edges.append((rel, target, "imports"))
        return edges

    def call_edges(self):
        """(caller_symbol, callee_symbol) resolved by callee name."""
        edges = []
        for rel, fi in self.files.items():
            for sym in fi.symbols:
                for callee in set(sym.calls):
                    for target in self.symbols.get(callee, []):
                        if target.file != rel or target.name != sym.name:
                            edges.append((f"{rel}:{sym.name}", f"{target.file}:{target.name}", "calls"))
        return edges

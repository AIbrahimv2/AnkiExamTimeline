#!/usr/bin/env python3
"""Run the Exam Timeline editor in a browser, outside Anki.

The page talks to the add-on's real bridge (src/bridge.py), with the exams
kept in a temporary JSON file instead of Anki's add-on config. Start it from
a copy of real exams with --exams (a JSON file holding {"exams": [...]}, such
as the add-on's meta.json), or from a few samples. Nothing is written back.

    python3 tools/devserver.py [--exams src/meta.json] [--port 5181]

Then open http://127.0.0.1:5181 (the built src/web/ bundle; add ?theme=dark
for dark mode), or run `npm run dev` in web/ for live reload at
http://localhost:5174 (it sends bridge calls here).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")

SHELL = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Exam Timeline (dev)</title>
<link rel="stylesheet" href="/web/app.css">
<script>
if (new URLSearchParams(location.search).get("theme") === "dark")
  document.documentElement.classList.add("night-mode");
window.pycmd = function (arg, cb) {
  fetch("/bridge", {method: "POST", body: arg}).then(r => r.json()).then(r => cb && cb(r));
  return false;
};
</script>
<script src="/web/app.js"></script>
</head><body><div id="root"></div></body></html>"""


def load_kit():
    """The shared add-on kit (src/kit/), as the editor window uses it for
    What's new and About. Outside Anki it knows only this add-on."""
    spec = importlib.util.spec_from_file_location(
        "kit", os.path.join(SRC, "kit", "__init__.py"), submodule_search_locations=[os.path.join(SRC, "kit")]
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["kit"] = mod
    spec.loader.exec_module(mod)
    mod.register("exam-timeline")
    return mod


def load_bridge():
    spec = importlib.util.spec_from_file_location("exam_timeline_bridge", os.path.join(SRC, "bridge.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Bridge


class FileStore:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> dict:
        with open(self.path) as f:
            return json.load(f)

    def save(self, cfg: dict) -> None:
        with open(self.path, "w") as f:
            json.dump(cfg, f, indent=2)


def samples() -> list[dict]:
    t = date.today()
    rows = [("B&B Exam 3", 1), ("B&B NBME", 4), ("USMLE Step 1", 75), ("MSK NBME", -59)]
    return [{"id": 1000 + i, "name": n, "date": (t + timedelta(days=d)).isoformat()} for i, (n, d) in enumerate(rows)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exams", help='a JSON file with {"exams": [...]} (or an add-on meta.json) to start from')
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5181)))
    args = ap.parse_args()

    exams = samples()
    if args.exams:
        with open(args.exams) as f:
            data = json.load(f)
        exams = (data.get("config") or data).get("exams", [])
    fd, path = tempfile.mkstemp(prefix="exam-timeline-dev-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump({"exams": exams}, f)
    bridge = load_bridge()(FileStore(path))
    kit = load_kit()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code: int, body: bytes, kind: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                return self._send(200, SHELL.encode(), "text/html; charset=utf-8")
            if path.startswith("/web/"):
                f = os.path.join(SRC, "web", os.path.basename(path))
                if os.path.isfile(f):
                    kind = "text/css" if f.endswith(".css") else "application/javascript"
                    with open(f, "rb") as fh:
                        return self._send(200, fh.read(), kind)
            self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path != "/bridge":
                return self._send(404, b"not found", "text/plain")
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
            msg = json.loads(raw)
            reply = kit.command(msg) if msg.get("cmd") == "kit" else bridge.handle(raw)
            self._send(200, json.dumps(reply).encode(), "application/json")

    print(f"Exam Timeline dev server on http://127.0.0.1:{args.port}  (exams in {path})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Make the screenshots for the README and the AnkiWeb listing.

    python3 tools/screenshots.py [--plain] [--capture-wallpaper | --wallpaper PATH]

Writes, at 2x and in dark mode, each a macOS window on the same macOS
wallpaper: Tahoe's dark one, which macOS 26 and later ship as a file.
--wallpaper uses another image, or a video's first frame. Wallpapers macOS
draws live (Sequoia's, say) have no file: --capture-wallpaper takes the one
the desktop shows now, on its own at the screen's full resolution, into
tools/wallpaper.png (Apple's artwork, so git leaves it out), and uses it.

- docs/screenshot.png: Anki's main window with the timeline on the deck
  screen, in AnkiGlass's Liquid Glass (--plain for stock Anki). It's Anki's
  own page markup and stylesheets (from the installed Anki.app) around the
  add-on's real widget, with AnkiGlass's own CSS (from ../anki-glass) and
  its window glass drawn as the wallpaper, blurred, under its tint.
- docs/editor.png: the editor, adding an exam with the date typed in words,
  above the exams and their countdowns. It's the built page (src/web/), run
  by tools/devserver.py. (The calendar is left closed: open, it covers the
  list.)

The exams and decks are made up, and dated from today. Needs Node and
Chromium (/Applications/Chromium.app, or set CHROMIUM), and AnkiGlass's
repo next to this one (or set ANKI_GLASS to its src/).
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import urllib.request
from datetime import date, timedelta
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
DOCS = os.path.join(ROOT, "docs")
ANKI_WEB = os.environ.get("ANKI_WEB", "/Applications/Anki.app/Contents/Resources/app_packages/_aqt/data/web")
WALLPAPER = "/System/Library/ExtensionKit/Extensions/NeptuneOneWallpaper.appex/Contents/Resources/TahoeDark.heic"
CAPTURED = os.path.join(ROOT, "tools", "wallpaper.png")  # made by --capture-wallpaper; not in git
SCREEN_WIDTH = 1512  # the wallpaper's width in the shots: a MacBook Pro 14"'s screen, in points
# Which part of it shows (CSS background-position). Of six wallpapers in nine
# crops each, measured for WCAG contrast of every word against what's behind
# it, Tahoe Dark's top left came out the best-looking of the legible ones:
# 33 of 36 pass, the rest near misses. Anki's coloured counts suffer most
# over a bright patch of wallpaper, so check them after changing this.
WALLPAPER_POSITION = "0% 0%"
ANKI_GLASS = os.environ.get("ANKI_GLASS", os.path.join(os.path.dirname(ROOT), "anki-glass", "src"))

# --- made-up exams and decks ---------------------------------------------------------

UPCOMING = [("Cardio Exam 2", 13), ("Cardio NBME", 17), ("Renal Exam 1", 29), ("USMLE Step 1", 101)]
PAST = [("B&B NBME", -4), ("MSK NBME", -60)]
NEW_EXAM = ("Pharm Exam 1", "in 3 weeks")  # what the editor shot is typing
# (depth, name, children shown: None (no children), "+" (collapsed) or "-", new, learn, due)
DECKS = [
    (0, "AnKing Step Deck", "+", 50, 8, 312),
    (0, "Lectures", "-", 40, 6, 78),
    (1, "Cardio", None, 30, 4, 57),
    (1, "Renal", None, 10, 2, 21),
    (0, "Pathoma", None, 0, 0, 14),  # under AnkiGlass, zeros are faint: keep them few
]
CURRENT_DECK = "AnKing Step Deck"
STUDIED = "Studied 186 cards in 31 minutes today (10.0s/card)."

MAIN_SIZE = (760, 622)  # the main window's content, below the title bar
EDITOR_SIZE = (560, 540)  # the editor window, just tall enough for the list


def exams() -> list[dict]:
    t = date.today()
    rows = UPCOMING + PAST
    return [{"id": 1000 + i, "name": n, "date": (t + timedelta(days=d)).isoformat()} for i, (n, d) in enumerate(rows)]


# --- the add-on's widget, outside Anki -----------------------------------------------


def load_addon():
    """src/__init__.py with stand-ins for what it imports from Anki."""
    aqt = types.ModuleType("aqt")
    aqt.mw = types.SimpleNamespace(addonManager=types.SimpleNamespace(setWebExports=lambda *a: None))
    aqt.gui_hooks = types.SimpleNamespace(
        main_window_did_init=[], deck_browser_will_render_content=[], overview_will_render_content=[],
        webview_did_receive_js_message=[])
    qt = types.ModuleType("aqt.qt")
    qt.QAction, qt.qconnect = object, lambda *a: None
    kit = types.ModuleType("examtl_shots.kit")
    kit.register = lambda *a: None
    editor = types.ModuleType("examtl_shots.editor")
    editor.open_editor = lambda: None
    sys.modules.update({"aqt": aqt, "aqt.qt": qt, "examtl_shots.kit": kit, "examtl_shots.editor": editor})
    spec = importlib.util.spec_from_file_location(
        "examtl_shots", os.path.join(SRC, "__init__.py"), submodule_search_locations=[SRC])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["examtl_shots"] = mod
    spec.loader.exec_module(mod)
    return mod


# --- AnkiGlass ---------------------------------------------------------------------------


def load_glass() -> dict:
    """AnkiGlass's CSS for each of the main window's pages, and its dark tint,
    read from its source (it can't be imported outside Anki): what its
    webview_will_set_content hook adds to each page in dark mode."""
    path = os.path.join(ANKI_GLASS, "__init__.py")
    if not os.path.isfile(path):
        raise SystemExit(f"AnkiGlass isn't at {ANKI_GLASS}: set ANKI_GLASS, or pass --plain")
    found = {}
    for node in ast.parse(open(path).read()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                found[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError:
                pass
    tint = found["_DEFAULTS"]["tint_dark"]
    root = f":root{{--lg-tint:{tint}}}\n"  # its tint_css()
    common = found["GLASS_COMMON_CSS"]
    return {
        "tint": tint,
        "toolbar": root + common + found["GLASS_TOP_CSS"],
        "deck": root + found["GLASS_CONTENT_CSS"] + found["GLASS_DECK_CSS"],
        "bottom": root + common + found["GLASS_BOTTOM_CSS"],
    }


# --- Anki's main window: toolbar, deck screen, bottom bar ----------------------------

# What AnkiWebView.stdHtml puts on every page on a Mac, and the body classes
# it gives them in dark mode.
STANDARD_CSS = """
body { zoom: 1; background-color: var(--canvas); }
html { font-family:"Helvetica"; }
button {
    --canvas: #fff;
    -webkit-appearance: none;
    background: var(--canvas);
    border-radius: var(--border-radius);
    padding: 3px 12px;
    border: 1px solid var(--border);
    box-shadow: 0px 1px 3px var(--border-subtle);
    font-family: Helvetica
}
.night-mode button { --canvas: #606060; --fg: #eee; }
"""
BODY_CLASS = "isMac nightMode night_mode fancy"


def anki_page(body: str, *css: str, extra: str = "") -> str:
    """A page as stdHtml makes it; `extra` is what add-ons add to its head."""
    links = "".join(f'<link rel="stylesheet" href="/_anki/css/{c}">' for c in ("webview.css", *css))
    extra = f"<style>{extra}</style>" if extra else ""
    return (
        '<!doctype html><html class="night-mode"><head><meta charset="utf-8">'
        f"<style>{STANDARD_CSS}</style>{links}{extra}</head>"
        f'<body class="{BODY_CLASS}">{body}</body></html>'
    )


def toolbar(glass: dict | None) -> str:
    links = [("decks", "Decks", "D"), ("add", "Add", "A"), ("browse", "Browse", "B"), ("stats", "Stats", "T"),
             ("sync", "Sync", "Y")]
    items = "".join(
        f'<a class=hitem tabindex="-1" aria-label="Shortcut key: {k}" title="Shortcut key: {k}" id="{i}" href=# '
        f"onclick=\"return pycmd('{i}')\">{label}"
        + ("<img id=sync-spinner src='/_anki/imgs/refresh.svg'>" if i == "sync" else "") + "</a>"
        for i, label, k in links)
    return anki_page(
        '<div class="header"><div class="left-tray"></div>'
        f'<div class="toolbar">{items}</div><div class="right-tray"></div></div>', "toolbar.css",
        extra=glass["toolbar"] if glass else "")


def deck_screen(addon, glass: dict | None) -> str:
    rows = [
        "<tr><th colspan=5 align=start>Deck</th><th class=count>New</th><th class=count>Learn</th>"
        "<th class=count>Due</th><th class=optscol></th></tr>",
        "<tr class='top-level-drag-row'><td colspan='6'>&nbsp;</td></tr>",
    ]
    for did, (depth, name, children, new, learn, due) in enumerate(DECKS, start=1):
        klass = "deck current" if name == CURRENT_DECK else "deck"
        collapse = (f"<a class=collapse href=# onclick='return pycmd(\"collapse:{did}\")'>{children}</a>"
                    if children else "<span class=collapse></span>")

        def count(n, kind):
            return f'<td align=end><span class="{kind if n else "zero-count"}">{n}</span></td>'

        rows.append(
            f"<tr class='{klass}' id='{did}'><td class=decktd colspan=5>{'&nbsp;' * 6 * depth}{collapse}"
            f"<a class=\"deck \" href=# onclick=\"return pycmd('open:{did}')\">{name}</a></td>"
            f"{count(new, 'new-count')}{count(learn, 'learn-count')}{count(due, 'review-count')}"
            f"<td align=center class=opts><a><img src='/_anki/imgs/gears.svg' class=gears></a></td></tr>")
    stats = f'<div id="studiedToday"><span>{STUDIED}</span></div>' + addon.build_timeline_widget(exams())
    body = f"<center>\n<table cellspacing=0 cellpadding=3>{''.join(rows)}</table>\n<br>\n{stats}</center>"
    return anki_page(body, "deckbrowser.css", extra=glass["deck"] if glass else "")


def bottom_bar(glass: dict | None) -> str:
    buttons = "".join(f"<button onclick='pycmd(\"{c}\");'>{label}</button>"
                      for c, label in (("shared", "Get Shared"), ("add", "Create Deck"), ("import", "Import File")))
    return anki_page(f"<center id=outer><table width=100% id=header><tr><td align=center>\n{buttons}</td></tr>"
                     "</table></center>", "toolbar.css", "toolbar-bottom.css", extra=glass["bottom"] if glass else "")


# Anki's three web views, one above the other, each sized to fit as Anki does.
# Under AnkiGlass they're see-through, so the page is left clear for the glass;
# its colour-scheme matches theirs, or Chromium paints the frames opaque.
MAIN_WINDOW = """<!doctype html><html><head><style>
:root { color-scheme: dark; }
html, body { margin: 0; height: 100%; background: BACKGROUND; }
body { display: flex; flex-direction: column; }
iframe { display: block; border: 0; width: 100%; flex: none; }
#main { flex: 1; }
</style></head><body>
<iframe id="top" src="toolbar.html"></iframe><iframe id="main" src="deck.html"></iframe>
<iframe id="bottom" src="bottom.html"></iframe>
<script>
window.shotReady = new Promise((resolve) => window.addEventListener('load', () => {
  for (const id of ['top', 'bottom']) {
    const f = document.getElementById(id);
    f.style.height = f.contentDocument.body.getBoundingClientRect().height
      + parseFloat(getComputedStyle(f.contentDocument.body).marginBottom) + 'px';
  }
  resolve(true);
}));
</script></body></html>"""

# --- the macOS window around each, on a wallpaper ----------------------------------

PAD = (52, 64, 76)  # wallpaper around the main window: top, sides, bottom
TITLE_BAR = 28
RADIUS = 16


def capture_wallpaper(out: str) -> None:
    """The desktop's wallpaper as it shows now, without the windows and icons
    on it: macOS draws it in a window of its own, which screencapture can
    take alone. Needs this app to be allowed to record the screen."""
    find = ('ObjC.import("CoreGraphics");'
            "const all = ObjC.deepUnwrap(ObjC.castRefToObject("
            "$.CGWindowListCopyWindowInfo($.kCGWindowListOptionAll, 0)));"
            'const w = all.find((w) => w.kCGWindowName === "Wallpaper" && w.kCGWindowLayer < -1000'
            " && w.kCGWindowBounds.X === 0 && w.kCGWindowBounds.Y === 0);"  # the main display's
            'w ? String(w.kCGWindowNumber) : ""')
    wid = subprocess.run(["osascript", "-l", "JavaScript", "-e", find],
                         capture_output=True, text=True).stdout.strip()
    if not wid:
        raise SystemExit("couldn't find the desktop's wallpaper: allow this app to record the screen "
                         "(System Settings > Privacy & Security > Screen & System Audio Recording)")
    subprocess.run(["screencapture", "-x", "-o", "-l", wid, out], check=True)
    print("captured the wallpaper to", os.path.relpath(out, ROOT))


def prepare_wallpaper(path: str, work: str) -> tuple:
    """The wallpaper as a PNG in `work`, and its size. macOS keeps its stills
    as HEIC, which Chromium can't show, and some only as videos."""
    if not os.path.isfile(path):
        if path == WALLPAPER:
            raise SystemExit("Tahoe's wallpaper isn't here (it needs macOS 26 or later): "
                             "pass --wallpaper or --capture-wallpaper")
        raise SystemExit(f"no wallpaper at {path}")
    out = os.path.join(work, "wallpaper.png")
    if path.lower().endswith((".mov", ".mp4", ".m4v")):
        # Quick Look's thumbnail of a video is its first frame.
        subprocess.run(["qlmanage", "-t", "-s", "3840", "-o", work, path], check=True, capture_output=True)
        os.replace(os.path.join(work, os.path.basename(path) + ".png"), out)
    else:
        subprocess.run(["sips", "-s", "format", "png", path, "--out", out], check=True, capture_output=True)
    sizes = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", out],
                           check=True, capture_output=True, text=True).stdout.split()
    return "wallpaper.png", int(sizes[-3]), int(sizes[-1])


def window(title: str, image: str, size: tuple, tint: str | None, wallpaper: tuple) -> str:
    """A macOS window holding `image`. With a tint, it's AnkiGlass's: the
    glass is the wallpaper behind it, blurred, under that tint, with no
    title bar of its own; without, a standard dark window."""
    w, h = size
    # Every shot is the same size and the same part of the desktop: the
    # wallpaper at a screen's scale, with the window centred across, and down
    # in the same proportion as the main window (its shadow falls below).
    name, ww, wh = wallpaper
    stage_w, stage_h = stage_size()
    assert w <= MAIN_SIZE[0] and h <= MAIN_SIZE[1], "the main window is the largest"
    left = (stage_w - w) / 2
    top = (stage_h - h - TITLE_BAR) * PAD[0] / (PAD[0] + PAD[2])
    scale = max(SCREEN_WIDTH / ww, stage_w / ww, stage_h / wh)
    backdrop = f"#1a1a2e url('{name}') {WALLPAPER_POSITION} / {ww * scale:.0f}px {wh * scale:.0f}px no-repeat"
    if tint:
        win = f"background: {tint}; backdrop-filter: blur(28px) saturate(150%);"
        rim, bar = "rgba(255,255,255,.2)", "background: transparent;"
    else:
        win = "background: #2c2c2c;"
        rim, bar = "rgba(255,255,255,.11)", "background: #353535; box-shadow: inset 0 -1px 0 rgba(0,0,0,.55);"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html, body {{ margin: 0; height: 100%; }}
body {{ background: {backdrop}; }}
.win {{ position: absolute; left: {left:g}px; top: {top:g}px; width: {w}px; border-radius: {RADIUS}px;
        overflow: hidden; {win}
        box-shadow: 0 0 0 .5px rgba(0,0,0,.7), 0 24px 60px rgba(0,0,0,.45), 0 6px 18px rgba(0,0,0,.25); }}
.win::after {{ content: ""; position: absolute; inset: 0; border-radius: {RADIUS}px; pointer-events: none;
               box-shadow: inset 0 0 0 1px {rim}; }}
.bar {{ position: relative; height: {TITLE_BAR}px; display: flex; align-items: center; justify-content: center;
        {bar} font: 600 13px -apple-system, system-ui, sans-serif; color: rgba(255,255,255,.85); }}
.lights {{ position: absolute; left: 13px; top: 8px; display: flex; gap: 8px; }}
.lights i {{ width: 12px; height: 12px; border-radius: 50%; box-shadow: inset 0 0 0 .5px rgba(0,0,0,.25); }}
img {{ display: block; width: {w}px; height: {h}px; }}
</style></head><body><div class="win"><div class="bar"><span class="lights">
<i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i></span>
{title}</div><img src="{image}"></div></body></html>"""


def stage_size() -> tuple:
    """Every shot's size: the main window's, with the wallpaper around it."""
    return MAIN_SIZE[0] + 2 * PAD[1], MAIN_SIZE[1] + TITLE_BAR + PAD[0] + PAD[2]


# --- the editor ------------------------------------------------------------------------

EDITOR_SETUP = """(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  for (let i = 0; i < 100 && !document.querySelector('.add .df-box input'); i++) await sleep(50);
  const type = (sel, text) => {
    const el = document.querySelector(sel);
    el.focus();
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, text);
    el.dispatchEvent(new Event('input', { bubbles: true }));
  };
  type('.add .field input', %s);
  await sleep(150);
  type('.add .df-box input', %s);
  await sleep(500);
  if (!document.querySelector('.add .cal')) throw new Error('the calendar did not open');
  // Close it as Esc does, leaving the typed date and how far away it is.
  document.querySelector('.add .df-box input')
    .dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  await sleep(300);
  if (document.querySelector('.add .cal')) throw new Error('the calendar did not close');
  return true;
})()""" % (json.dumps(NEW_EXAM[0]), json.dumps(NEW_EXAM[1]))

# --- running it ------------------------------------------------------------------------


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(folder: str) -> ThreadingHTTPServer:
    """The pages, with Anki's own files under /_anki/ as Anki serves them."""

    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            if path.startswith("/_anki/"):
                return os.path.join(ANKI_WEB, path[len("/_anki/"):].split("?")[0])
            return super().translate_path(path)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=folder))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def wait_for(url: str, timeout: float = 15) -> None:
    t = time.time()
    while time.time() - t < timeout:
        try:
            urllib.request.urlopen(url, timeout=1).read()
            return
        except OSError:
            time.sleep(0.2)
    raise SystemExit(f"{url} didn't answer")


def capture(work: str, shots: list[dict]) -> None:
    path = os.path.join(work, "shots.json")
    with open(path, "w") as f:
        json.dump(shots, f)
    subprocess.run(["node", os.path.join(ROOT, "tools", "capture.mjs"), path], check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plain", action="store_true", help="stock Anki, without AnkiGlass")
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--capture-wallpaper", action="store_true",
                       help="use the desktop's wallpaper as it shows now (saved to tools/wallpaper.png)")
    which.add_argument("--wallpaper", default=WALLPAPER, help="an image, or a video to take the first frame of")
    args = ap.parse_args()
    if args.capture_wallpaper:
        capture_wallpaper(CAPTURED)
        args.wallpaper = CAPTURED
    if not os.path.isdir(ANKI_WEB):
        raise SystemExit(f"Anki's web files aren't at {ANKI_WEB}: set ANKI_WEB")
    addon = load_addon()
    glass = None if args.plain else load_glass()
    work = tempfile.mkdtemp(prefix="exam-timeline-shots-")
    dev = None
    try:
        main_window = MAIN_WINDOW.replace("BACKGROUND", "transparent" if glass else "#2c2c2c")
        for name, page in (("toolbar.html", toolbar(glass)), ("deck.html", deck_screen(addon, glass)),
                           ("bottom.html", bottom_bar(glass)), ("main.html", main_window)):
            with open(os.path.join(work, name), "w") as f:
                f.write(page)
        srv = serve(work)
        base = f"http://127.0.0.1:{srv.server_address[1]}"

        with open(os.path.join(work, "exams.json"), "w") as f:
            json.dump({"exams": exams()}, f)
        port = free_port()
        dev = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "devserver.py"), "--port", str(port),
                                "--exams", os.path.join(work, "exams.json")],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_for(f"http://127.0.0.1:{port}/")

        capture(work, [
            {"url": f"{base}/main.html", "width": MAIN_SIZE[0], "height": MAIN_SIZE[1], "setup": "window.shotReady",
             "transparent": bool(glass), "out": os.path.join(work, "main.png")},
            {"url": f"http://127.0.0.1:{port}/?theme=dark", "width": EDITOR_SIZE[0], "height": EDITOR_SIZE[1],
             "setup": EDITOR_SETUP, "wait": 900, "out": os.path.join(work, "editor-raw.png")},
        ])
        wallpaper = prepare_wallpaper(args.wallpaper, work)
        # AnkiGlass puts glass under the main window only: the editor stays solid.
        for name, title, image, size, tint in (
                ("window-main.html", "User 1 - Anki", "main.png", MAIN_SIZE, glass and glass["tint"]),
                ("window-editor.html", "Exam Timeline", "editor-raw.png", EDITOR_SIZE, None)):
            with open(os.path.join(work, name), "w") as f:
                f.write(window(title, image, size, tint, wallpaper))
        os.makedirs(DOCS, exist_ok=True)
        shots = []
        for name, size, out in (("window-main.html", MAIN_SIZE, "screenshot.png"),
                                ("window-editor.html", EDITOR_SIZE, "editor.png")):
            w, h = stage_size()
            shots.append({"url": f"{base}/{name}", "width": w, "height": h, "wait": 300,
                          "out": os.path.join(DOCS, out)})
        capture(work, shots)
        for s in shots:
            print("wrote", os.path.relpath(s["out"], ROOT))
    finally:
        if dev:
            dev.terminate()
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Make the screenshots for the README and the AnkiWeb listing.

    python3 tools/screenshots.py [--plain] [--capture-wallpaper | --wallpaper PATH]

Writes docs/screenshot.png, Anki's main window with the timeline on the deck
screen (in AnkiGlass; --plain for stock Anki), and docs/editor.png, the
editor adding an exam with its date typed in words, above the exams and
their countdowns (the calendar left closed: open, it covers the list).

They're made with the add-ons' shared screenshot tools, in the kit's
checkout next to this one (../anki-addon-kit/screenshots/shots.py, or set
ANKI_ADDON_KIT), which describe how they look and what they need. The
widget is the add-on's real code, the editor its built page (src/web/) run
by tools/devserver.py. The exams are made up and dated from today.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import types
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
DOCS = os.path.join(ROOT, "docs")
KIT = os.environ.get("ANKI_ADDON_KIT", os.path.join(os.path.dirname(ROOT), "anki-addon-kit"))
sys.path.insert(0, os.path.join(KIT, "screenshots"))
import shots  # noqa: E402

UPCOMING = [("Cardio Exam 2", 13), ("Cardio NBME", 17), ("Renal Exam 1", 29), ("USMLE Step 1", 101)]
PAST = [("B&B NBME", -4), ("MSK NBME", -60)]
NEW_EXAM = ("Pharm Exam 1", "in 3 weeks")  # what the editor shot is typing
# Fewer decks than the kit's, to leave room for the timeline under them.
DECKS = [
    (0, "AnKing Step Deck", "+", 50, 8, 312),
    (0, "Lectures", "-", 40, 6, 78),
    (1, "Cardio", None, 30, 4, 57),
    (1, "Renal", None, 10, 2, 21),
    (0, "Pathoma", None, 0, 0, 14),
]
EDITOR_SIZE = (560, 540)  # the editor window, just tall enough for the list


def exams() -> list[dict]:
    t = date.today()
    rows = UPCOMING + PAST
    return [{"id": 1000 + i, "name": n, "date": (t + timedelta(days=d)).isoformat()} for i, (n, d) in enumerate(rows)]


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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plain", action="store_true", help="stock Anki, without AnkiGlass")
    shots.add_wallpaper_args(ap)
    args = ap.parse_args()
    addon = load_addon()
    glass = None if args.plain else shots.load_glass()
    with shots.Session() as s:
        deck = s.main_window("deck", shots.toolbar(glass),
                             shots.deck_browser(glass, DECKS, stats=addon.build_timeline_widget(exams())),
                             shots.deck_browser_bar(glass), glass)
        with open(s.path("exams.json"), "w") as f:
            json.dump({"exams": exams()}, f)
        port = shots.free_port()
        dev = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "devserver.py"), "--port", str(port),
                                "--exams", s.path("exams.json")],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            shots.wait_for(f"http://127.0.0.1:{port}/")
            s.capture([
                {"url": deck, "width": shots.MAIN_SIZE[0], "height": shots.MAIN_SIZE[1],
                 "setup": "window.shotReady", "transparent": bool(glass), "out": "deck.png"},
                {"url": f"http://127.0.0.1:{port}/?theme=dark", "width": EDITOR_SIZE[0], "height": EDITOR_SIZE[1],
                 "setup": EDITOR_SETUP, "wait": 900, "out": "editor.png"},
            ])
        finally:
            dev.terminate()
        # AnkiGlass puts glass under the main window only: the editor stays solid.
        written = s.frames([
            {"image": "deck.png", "size": shots.MAIN_SIZE, "title": "User 1 - Anki",
             "tint": glass and glass["tint"], "out": "screenshot.png"},
            {"image": "editor.png", "size": EDITOR_SIZE, "title": "Exam Timeline", "out": "editor.png"},
        ], shots.wallpaper_for(args, s), DOCS)
    for out in written:
        print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()

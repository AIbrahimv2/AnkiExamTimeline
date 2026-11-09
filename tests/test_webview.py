"""Open the real editor window (AnkiWebView and its pycmd bridge) offscreen with
a stand-in for Anki's main window, and use it the way a person would: type a
date, pick one from the calendar with the mouse and with the keyboard, add,
edit, remove and undo. Run with Anki's own Python (tests/run.sh does).

Also checks the page never puts up a control with a native popup (a date
input, a select): those crash Anki's web view on macOS."""

import json
import os
import sys
import threading
import time
import types
from calendar import monthrange
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

S = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(S), "src")
ANKI = "/Applications/Anki.app/Contents/Resources/app_packages"
ANKI_WEB = os.path.join(ANKI, "_aqt/data/web")
PORT = 5198
FOLDER = "examtl"  # the add-on's folder name in Anki, without the hyphen

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, ANKI)
link = os.path.join(S, "fixture", "pkgs", FOLDER)
os.makedirs(os.path.dirname(link), exist_ok=True)
if not os.path.islink(link):
    os.symlink(SRC, link)
sys.path.insert(0, os.path.dirname(link))

from aqt.qt import QApplication, QEvent, QKeyEvent, QMenu, Qt, QWidget  # noqa: E402

app = QApplication.instance() or QApplication(["test"])
import aqt  # noqa: E402

TODAY = date.today()
iso = lambda days: (TODAY + timedelta(days=days)).isoformat()  # noqa: E731


class AddonManager:
    def __init__(self):
        self.cfg = {"exams": [
            {"id": 1, "name": "B&B NBME", "date": iso(4)},
            {"id": 2, "name": "MSK NBME", "date": iso(-59)},
        ]}

    def getConfig(self, module):
        return json.loads(json.dumps(self.cfg))

    def writeConfig(self, module, cfg):
        self.cfg = json.loads(json.dumps(cfg))

    def addonFromModule(self, module):
        return module.split(".")[0]

    def setWebExports(self, module, pattern):
        pass


PAGES = {}


class Server(BaseHTTPRequestHandler):
    """Anki's media server, for what the page loads."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/_anki/legacyPageData":
            return self.reply(PAGES.get(self.path.split("id=")[-1], "").encode(), "text/html; charset=utf-8")
        for prefix, root in (("/_anki/", ANKI_WEB), (f"/_addons/{FOLDER}/web/", os.path.join(SRC, "web"))):
            f = os.path.join(root, path[len(prefix):])
            if path.startswith(prefix) and os.path.isfile(f):
                with open(f, "rb") as fh:
                    return self.reply(fh.read(), "text/css" if f.endswith(".css") else "application/javascript")
        self.send_response(404)
        self.end_headers()

    def reply(self, body, kind):
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.end_headers()
        self.wfile.write(body)


srv = ThreadingHTTPServer(("127.0.0.1", PORT), Server)
threading.Thread(target=srv.serve_forever, daemon=True).start()

mw = QWidget()
mw.addonManager = AddonManager()
mw.col = types.SimpleNamespace()  # Anki ignores page messages when no collection is open
mw.state = "deckBrowser"
REFRESHES = []
mw.deckBrowser = types.SimpleNamespace(refresh=lambda: REFRESHES.append(1))
mw.form = types.SimpleNamespace(menuTools=QMenu())
mw.app = app
mw.mediaServer = types.SimpleNamespace(
    getPort=lambda: PORT, set_page_html=lambda pid, html, ctx: PAGES.__setitem__(str(pid), html))
mw.serverURL = lambda: f"http://127.0.0.1:{PORT}/"
mw.baseHTML = lambda: f'<base href="http://127.0.0.1:{PORT}/">'
mw.pm = types.SimpleNamespace(minimalist_mode=lambda: False, reduce_motion=lambda: False)
aqt.mw = mw

import examtl  # noqa: E402,F401
from examtl import editor  # noqa: E402

editor.restoreGeom = editor.saveGeom = lambda *a, **k: None
editor.open_editor()
d = editor._dialog
exams = lambda: mw.addonManager.cfg["exams"]  # noqa: E731


def pump(n=5):
    for _ in range(n):
        app.processEvents()


def js(expr, timeout=8.0):
    done = []
    d.web.evalWithCallback(expr, lambda r: done.append(r))
    t = time.time()
    while not done and time.time() - t < timeout:
        pump()
        time.sleep(0.02)
    return done[0] if done else "<timeout>"


def wait_for(expr, timeout=15.0):
    t = time.time()
    while time.time() - t < timeout:
        pump()
        v = js(expr, 2)
        if v not in (None, False, 0, "", "<timeout>"):
            return v
        time.sleep(0.1)
    return None


def settle(n=6):
    for _ in range(n):
        pump()
        time.sleep(0.03)


# React reads what's typed from input events, so set values the way typing does.
js("""window.typeInto = (sel, text) => {
  const el = document.querySelector(sel);
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, text);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
}; 1""")
NATIVE = "document.querySelectorAll('select, datalist').length + [...document.querySelectorAll('input')].filter((i) => i.type !== 'text').length"
HINT = "document.querySelector('.add .df-hint').textContent"
ADD_DATE = ".add .df-box input"


def typed(sel, text):
    assert wait_for("!!window.typeInto"), "page script"
    js(f"typeInto({json.dumps(sel)}, {json.dumps(text)})")
    settle()


def click(sel):
    assert js(f"(() => {{ const e = document.querySelector({json.dumps(sel)}); e && e.click(); return !!e; }})()"), sel
    settle()


# Real key presses, through Qt, as Anki gets them.
proxy = lambda: d.web.focusProxy() or d.web  # noqa: E731
KEYS = {"Down": (Qt.Key.Key_Down, ""), "Right": (Qt.Key.Key_Right, ""), "Enter": (Qt.Key.Key_Return, "\r"),
        "Escape": (Qt.Key.Key_Escape, "\x1b"), "PageDown": (Qt.Key.Key_PageDown, "")}


def key(name):
    k, text = KEYS[name]
    for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
        QApplication.sendEvent(proxy(), QKeyEvent(kind, k, Qt.KeyboardModifier.NoModifier, text))
    settle(10)


# --- it opens with the exams ------------------------------------------------------
assert wait_for("document.querySelectorAll('.exam').length === 1"), "the upcoming exam shows"
assert js("document.querySelector('.exam-name').textContent") == "B&B NBME"
assert js("document.querySelector('.exam-unit').textContent") == "days left"
assert js("document.querySelector('.past-toggle').textContent") == "Past 1"
assert js(NATIVE) == 0, "no native-popup controls"
print("opens with the exams")

# --- typing a date --------------------------------------------------------------------
typed(ADD_DATE, "in 3 weeks")
want = TODAY + timedelta(days=21)
assert js(HINT) == want.strftime("%A, %B ") + str(want.day) + want.strftime(", %Y") + "in 21 days", js(HINT)
typed(ADD_DATE, "nov 31")
assert js(HINT) == "November has only 30 days.", js(HINT)
assert js("document.querySelector('.add .df-box').classList.contains('bad')")
typed(ADD_DATE, "in 3 weeks")
click(".add-btn")
assert js("document.querySelector('.form-error').textContent") == "Give the exam a name.", "a name is needed"
assert len(exams()) == 2, "nothing added yet"
typed(".add > input", "USMLE Step 1")
click(".add-btn")
assert wait_for("document.querySelectorAll('.exam').length === 2"), "added"
assert any(e["name"] == "USMLE Step 1" and e["date"] == want.isoformat() for e in exams()), exams()
assert REFRESHES, "the deck screen redraws"
assert js("document.querySelector('.toast').textContent") == "Added USMLE Step 1"
assert js("document.querySelector('.add > input').value") == "" and js(f"document.querySelector('{ADD_DATE}').value") == ""
print("typing a date works")

# --- picking one with the mouse ------------------------------------------------------
click(".add .df-cal")
assert wait_for("document.querySelectorAll('.cal .cal-day').length === 42"), "the calendar opens"
assert js(NATIVE) == 0
assert js("document.querySelector('.cal .cal-day.today').textContent") == str(TODAY.day)
assert js("document.querySelectorAll('.cal .cal-dot').length") >= 1, "exam days carry a dot"
click(".cal .chip")  # In 1 week
want = TODAY + timedelta(days=7)
assert not js("!!document.querySelector('.cal')"), "picking closes it"
assert js(HINT).endswith("in 7 days"), js(HINT)
typed(".add > input", "Shelf")
click(".add-btn")
assert wait_for("document.querySelectorAll('.exam').length === 3")
assert any(e["name"] == "Shelf" and e["date"] == want.isoformat() for e in exams())
print("picking from the calendar works")

# --- and with the keyboard ------------------------------------------------------------
js(f"document.querySelector('{ADD_DATE}').focus(); 1")
d.web.setFocus()
settle()
key("Down")
assert wait_for("document.activeElement.classList.contains('cal-grid')"), "Down opens the calendar and focuses it"
key("PageDown")
key("Right")
key("Enter")
assert not js("!!document.querySelector('.cal')")
assert js("document.activeElement.matches('.add .df-box input')"), "focus goes back to the field"
y, m = divmod(TODAY.month, 12)
y, m = TODAY.year + y, m + 1
picked = date(y, m, min(TODAY.day, monthrange(y, m)[1])) + timedelta(days=1)  # a month on, a day on
assert js(HINT).startswith(picked.strftime("%A, %B ") + str(picked.day)), (js(HINT), picked)
key("Down")
assert wait_for("!!document.querySelector('.cal')")
key("Escape")
assert not js("!!document.querySelector('.cal')"), "Esc closes the calendar"
assert d.isVisible(), "and not the window"
print("calendar keys work")

# --- edit, remove, undo ---------------------------------------------------------------
click('[aria-label="Edit B&B NBME"]')
assert wait_for("!!document.querySelector('.exam.editing')")
assert js(NATIVE) == 0
typed(".exam.editing .df-box input", "in 5 days")
click(".exam.editing .btn.primary")
assert wait_for("!document.querySelector('.exam.editing')"), "saved"
assert next(e for e in exams() if e["id"] == 1)["date"] == iso(5)
click('[aria-label="Edit B&B NBME"]')
key("Escape")
assert not js("!!document.querySelector('.exam.editing')"), "Esc cancels editing"
assert d.isVisible()

click('[aria-label="Remove Shelf"]')
assert wait_for("document.querySelectorAll('.exam').length === 2")
assert not any(e["name"] == "Shelf" for e in exams())
click(".toast .btn")
assert wait_for("document.querySelectorAll('.exam').length === 3"), "Undo puts it back"
assert any(e["name"] == "Shelf" for e in exams())
print("edit, remove and undo work")

# --- reopening reloads -------------------------------------------------------------------
mw.addonManager.cfg["exams"].append({"id": 9, "name": "Added elsewhere", "date": iso(30)})
d.hide()
editor.open_editor()
assert editor._dialog is d, "one window"
assert wait_for("document.querySelectorAll('.exam').length === 4"), "reopening shows changes made elsewhere"
print("reopening reloads")

print("\nWEBVIEW TEST PASSED")
srv.shutdown()
# QtWebEngine can crash in its own teardown after the test has finished: leave
# without it, so a non-zero exit always means a real failure.
sys.stdout.flush()
os._exit(0)

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""Exam Timeline — a horizontal countdown timeline of upcoming exams for Anki.

A read-only timeline widget is shown on the deck browser (home) screen with a
large "days left" countdown per exam. Exams are added and removed from a
separate editor window (Tools -> Exam Timeline, or the "Edit" button on the
widget). Data is stored in the add-on config.
"""

from __future__ import annotations

import html as _html
import json
import time
from datetime import date

from aqt import gui_hooks, mw
from aqt.deckbrowser import DeckBrowser
from aqt.qt import QAction, QDialog, QVBoxLayout, qconnect
from aqt.utils import restoreGeom, saveGeom
from aqt.webview import AnkiWebView

GEOM_KEY = "exam_timeline"
OPEN_CMD = "examtl:open"


# --- data --------------------------------------------------------------------


def get_config() -> dict:
    cfg = mw.addonManager.getConfig(__name__) or {}
    if not isinstance(cfg.get("exams"), list):
        cfg["exams"] = []
    return cfg


def save_config(cfg: dict) -> None:
    mw.addonManager.writeConfig(__name__, cfg)


def days_left(iso: str):
    try:
        return (date.fromisoformat(iso) - date.today()).days
    except Exception:
        return None


def upcoming(exams: list) -> list:
    """Exams from today onward, sorted nearest-first, as (exam, days) tuples."""
    rows = []
    for e in exams:
        d = days_left(e.get("date", ""))
        if d is not None and d >= 0:
            rows.append((e, d))
    rows.sort(key=lambda x: x[1])
    return rows


# --- timeline widget (deck browser) ------------------------------------------

TIMELINE_STYLE = """
<style>
.et-wrap { padding: 18px 26px 14px; font-family: -apple-system, system-ui, sans-serif;
           color: var(--fg, #1a1a1a); text-align: left; }
.et-head { display: flex; align-items: center; gap: 10px; margin: 0 0 2px; }
.et-head .et-title { font-size: 12px; font-weight: 700; letter-spacing: .08em;
                     text-transform: uppercase; opacity: .55; }
.et-head .et-edit { margin-left: auto; font-size: 12px; font-weight: 600; color: #3b82f6;
                    background: transparent; border: none; cursor: pointer; padding: 3px 8px;
                    border-radius: 7px; }
.et-head .et-edit:hover { background: rgba(59,130,246,.12); }

.et-focus { display: flex; align-items: center; justify-content: center; gap: 6px; }
.et-nav { border: none; background: transparent; color: var(--fg, #888); opacity: .3;
          font-size: 30px; line-height: 1; cursor: pointer; padding: 4px 12px; border-radius: 10px;
          user-select: none; transition: opacity .15s, background .15s; }
.et-nav:hover { opacity: 1; background: rgba(127,127,127,.12); }
.et-hero { flex: 1; text-align: center; padding: 4px 0 2px; min-width: 0; }
.et-count { font-size: 76px; font-weight: 800; line-height: .95; letter-spacing: -.03em;
            color: #3b82f6; transition: color .2s; }
.et-unit { font-size: 12px; text-transform: uppercase; letter-spacing: .1em; opacity: .55;
           margin-top: 2px; }
.et-name { font-size: 19px; font-weight: 700; margin-top: 12px; word-break: break-word; }
.et-date { font-size: 13px; opacity: .55; margin-top: 3px; }
.et-hero.near .et-count { color: #f59e0b; }
.et-hero.soon .et-count { color: #ef4444; }

.et-track { position: relative; height: 30px; margin: 14px 14px 0; }
.et-rail { position: absolute; left: 0; right: 0; top: 13px; height: 2px;
           background: var(--border, #e0e0e0); }
.et-tick { position: absolute; top: 13px; transform: translate(-50%, -50%); width: 10px;
           height: 10px; border-radius: 50%; background: var(--border, #c4c4c4);
           border: 2px solid var(--canvas, #fff); cursor: pointer;
           transition: width .15s, height .15s, background .15s, box-shadow .15s; }
.et-tick:hover { background: #9aa0a6; }
.et-tick.active { width: 16px; height: 16px; background: #3b82f6;
                  box-shadow: 0 0 0 4px rgba(59,130,246,.18); }
.et-tick.active.near { background: #f59e0b; box-shadow: 0 0 0 4px rgba(245,158,11,.18); }
.et-tick.active.soon { background: #ef4444; box-shadow: 0 0 0 4px rgba(239,68,68,.18); }
.et-today { position: absolute; left: 0; top: 22px; font-size: 10px; opacity: .4;
            text-transform: uppercase; letter-spacing: .06em; }
.et-counter { text-align: center; font-size: 11px; opacity: .4; margin-top: 4px;
              letter-spacing: .05em; }

.et-empty { opacity: .55; font-size: 13px; padding: 14px 2px; }
.et-empty a { color: #3b82f6; cursor: pointer; text-decoration: none; }
.et-empty a:hover { text-decoration: underline; }
</style>
"""

WIDGET_SCRIPT = """
<script>
(function () {
  var EXAMS = __DATA__;
  var root = document.getElementById('et-widget');
  if (!root || !EXAMS.length) { return; }
  var focus = 0;
  var maxDays = Math.max(1, EXAMS[EXAMS.length - 1].days);
  var hero = root.querySelector('.et-hero');
  var countEl = root.querySelector('.et-count');
  var unitEl = root.querySelector('.et-unit');
  var nameEl = root.querySelector('.et-name');
  var dateEl = root.querySelector('.et-date');
  var counterEl = root.querySelector('.et-counter');
  var track = root.querySelector('.et-track');
  var ticks = [];
  Array.prototype.forEach.call(track.querySelectorAll('.et-tick'), function (t) { t.remove(); });

  function urg(d) { return d <= 7 ? 'soon' : (d <= 30 ? 'near' : ''); }
  function posPct(d) { return EXAMS.length === 1 ? 50 : (6 + (d / maxDays) * 88); }

  EXAMS.forEach(function (e, i) {
    var t = document.createElement('div');
    t.className = 'et-tick ' + urg(e.days);
    t.style.left = posPct(e.days) + '%';
    t.title = e.name + ' \\u2014 ' + e.pretty;
    t.addEventListener('click', function () { focus = i; render(); });
    track.appendChild(t);
    ticks.push(t);
  });

  function render() {
    var e = EXAMS[focus];
    hero.className = 'et-hero ' + urg(e.days);
    countEl.textContent = e.days === 0 ? '0' : String(e.days);
    unitEl.textContent = e.days === 0 ? 'today' : (e.days === 1 ? 'day left' : 'days left');
    nameEl.textContent = e.name;
    dateEl.textContent = e.pretty;
    counterEl.textContent = (focus + 1) + ' / ' + EXAMS.length;
    ticks.forEach(function (t, i) {
      t.className = 'et-tick ' + urg(EXAMS[i].days) + (i === focus ? ' active' : '');
    });
  }

  root.querySelector('.et-prev').addEventListener('click', function () {
    focus = (focus - 1 + EXAMS.length) % EXAMS.length; render();
  });
  root.querySelector('.et-next').addEventListener('click', function () {
    focus = (focus + 1) % EXAMS.length; render();
  });
  if (EXAMS.length < 2) {
    root.querySelectorAll('.et-nav').forEach(function (n) { n.style.visibility = 'hidden'; });
  }
  render();
})();
</script>
"""


def _urgency(d: int) -> str:
    return "soon" if d <= 7 else ("near" if d <= 30 else "")


def _pretty_date(iso: str) -> str:
    try:
        dt = date.fromisoformat(iso)
        return dt.strftime("%a, %b ") + str(dt.day) + dt.strftime(", %Y")
    except Exception:
        return iso


def _widget_data(exams: list) -> list:
    """Upcoming exams (nearest first) as plain dicts for client-side rendering."""
    data = []
    for e, d in upcoming(exams):
        iso = e.get("date", "")
        data.append({"name": e.get("name", ""), "date": iso, "pretty": _pretty_date(iso), "days": d})
    return data


def _head() -> str:
    return (
        '<div class="et-head"><span class="et-title">Exam Timeline</span>'
        f"<button class=\"et-edit\" onclick=\"pycmd('{OPEN_CMD}')\">Edit</button></div>"
    )


def build_timeline_widget(exams: list) -> str:
    data = _widget_data(exams)
    if not data:
        return (
            f'<div class="et-wrap">{_head()}'
            '<div class="et-empty">No upcoming exams — '
            f"<a onclick=\"pycmd('{OPEN_CMD}')\">add one</a>.</div></div>{TIMELINE_STYLE}"
        )
    body = (
        f'<div class="et-wrap" id="et-widget">{_head()}'
        '<div class="et-focus">'
        '<button class="et-nav et-prev" aria-label="Previous">&lsaquo;</button>'
        '<div class="et-hero"><div class="et-count"></div><div class="et-unit"></div>'
        '<div class="et-name"></div><div class="et-date"></div></div>'
        '<button class="et-nav et-next" aria-label="Next">&rsaquo;</button>'
        "</div>"
        '<div class="et-track"><div class="et-rail"></div><span class="et-today">Today</span></div>'
        '<div class="et-counter"></div>'
        "</div>"
    )
    payload = json.dumps(data).replace("</", "<\\/")
    return body + TIMELINE_STYLE + WIDGET_SCRIPT.replace("__DATA__", payload)


def on_webview_content(web_content, context) -> None:
    """Prepend the read-only timeline to the top of the deck browser page."""
    if isinstance(context, DeckBrowser):
        web_content.body = build_timeline_widget(get_config()["exams"]) + web_content.body


def on_js_message(handled, message: str, context):
    if message == OPEN_CMD:
        open_editor()
        return (True, None)
    return handled


# --- editor window -----------------------------------------------------------

EDITOR_STYLE = """
<style>
.ed-wrap { padding: 22px 26px 30px; font-family: -apple-system, system-ui, sans-serif;
           color: var(--fg, #1a1a1a); }
.ed-wrap h1 { font-size: 20px; font-weight: 700; margin: 0 0 4px; }
.ed-wrap .ed-sub { font-size: 13px; opacity: .5; margin-bottom: 20px; }
.ed-form { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 24px; }
.ed-in { padding: 9px 11px; border-radius: 9px; border: 1px solid var(--border, #ccc);
         background: var(--canvas-elevated, #fff); color: var(--fg, #000); font-size: 14px; }
#ed-name { flex: 1; min-width: 200px; }
.ed-add { padding: 9px 18px; border: none; border-radius: 9px; background: #3b82f6;
          color: #fff; font-weight: 600; cursor: pointer; font-size: 14px; }
.ed-add:hover { background: #2563eb; }
.ed-list { display: flex; flex-direction: column; gap: 8px; }
.ed-row { display: flex; align-items: center; gap: 14px; padding: 12px 14px;
          border: 1px solid var(--border, #e2e2e2); border-radius: 11px;
          background: var(--canvas-elevated, #fff); }
.ed-days { font-size: 22px; font-weight: 800; min-width: 62px; text-align: center;
           line-height: 1; }
.ed-days small { display: block; font-size: 9px; font-weight: 600; text-transform: uppercase;
                 letter-spacing: .06em; opacity: .5; margin-top: 3px; }
.ed-info { flex: 1; }
.ed-info .ed-nm { font-size: 15px; font-weight: 600; }
.ed-info .ed-dt { font-size: 12px; opacity: .55; margin-top: 2px; }
.ed-row.near .ed-days { color: #f59e0b; }
.ed-row.soon .ed-days { color: #ef4444; }
.ed-row.past { opacity: .5; }
.ed-row.past .ed-days { color: var(--fg, #888); }
.ed-del { border: none; background: transparent; color: var(--fg, #888); opacity: .4;
          font-size: 20px; line-height: 1; cursor: pointer; padding: 2px 6px; border-radius: 7px; }
.ed-del:hover { opacity: 1; color: #ef4444; background: rgba(239,68,68,.12); }
.ed-empty { opacity: .55; padding: 30px 0; text-align: center; font-size: 14px; }
</style>
"""

EDITOR_SCRIPT = """
<script>
function edAdd() {
  var n = document.getElementById('ed-name').value.trim();
  var d = document.getElementById('ed-date').value;
  if (!n || !d) { return; }
  pycmd('add:' + JSON.stringify({name: n, date: d}));
}
function edDel(id) { pycmd('del:' + id); }
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && (e.target.id === 'ed-name' || e.target.id === 'ed-date')) edAdd();
});
</script>
"""


def _editor_row(exam: dict) -> str:
    name = _html.escape(exam.get("name", ""))
    iso = _html.escape(exam.get("date", ""))
    eid = _html.escape(str(exam.get("id", "")))
    d = days_left(exam.get("date", ""))
    if d is None:
        cls, big, unit = "past", "—", ""
    elif d < 0:
        cls, big, unit = "past", str(-d), "days ago"
    else:
        cls = _urgency(d)
        big = "0" if d == 0 else str(d)
        unit = "today" if d == 0 else ("day left" if d == 1 else "days left")
    return f"""
      <div class="ed-row {cls}">
        <div class="ed-days">{big}<small>{unit}</small></div>
        <div class="ed-info"><div class="ed-nm">{name}</div><div class="ed-dt">{iso}</div></div>
        <button class="ed-del" title="Remove" onclick="edDel('{eid}')">&times;</button>
      </div>
    """


def build_editor(exams: list) -> str:
    def sort_key(e):
        d = days_left(e.get("date", ""))
        return (d is None, d if d is not None else 0)

    ordered = sorted(exams, key=sort_key)
    out = ['<div class="ed-wrap">']
    out.append("<h1>Exam Timeline</h1>")
    out.append('<div class="ed-sub">Add your upcoming exams — they appear on the deck screen.</div>')
    out.append(
        '<div class="ed-form">'
        '<input id="ed-name" class="ed-in" placeholder="Exam name (e.g. USMLE Step 1)" />'
        '<input id="ed-date" class="ed-in" type="date" />'
        '<button class="ed-add" onclick="edAdd()">Add exam</button>'
        "</div>"
    )
    if not ordered:
        out.append('<div class="ed-empty">No exams yet. Add one above to get started.</div>')
    else:
        out.append('<div class="ed-list">')
        out.extend(_editor_row(e) for e in ordered)
        out.append("</div>")
    out.append("</div>")
    out.append(EDITOR_STYLE)
    out.append(EDITOR_SCRIPT)
    return "".join(out)


def refresh_widget() -> None:
    if mw.state == "deckBrowser":
        mw.deckBrowser.refresh()


class EditorDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Exam Timeline")
        self.resize(560, 560)
        restoreGeom(self, GEOM_KEY)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.web = AnkiWebView(self, title="exam_timeline_editor")
        self.web.set_bridge_command(self._on_cmd, self)
        layout.addWidget(self.web)

    def refresh(self) -> None:
        self.web.stdHtml(build_editor(get_config()["exams"]))

    def _on_cmd(self, cmd: str):
        changed = False
        if cmd.startswith("add:"):
            try:
                data = json.loads(cmd[4:])
            except Exception:
                return None
            name = (data.get("name") or "").strip()
            d = (data.get("date") or "").strip()
            if name and d:
                cfg = get_config()
                cfg["exams"].append({"id": int(time.time() * 1000), "name": name, "date": d})
                save_config(cfg)
                changed = True
        elif cmd.startswith("del:"):
            rid = cmd[4:]
            cfg = get_config()
            cfg["exams"] = [e for e in cfg["exams"] if str(e.get("id")) != rid]
            save_config(cfg)
            changed = True
        if changed:
            self.refresh()
            refresh_widget()
        return None

    def closeEvent(self, ev) -> None:
        saveGeom(self, GEOM_KEY)
        super().closeEvent(ev)


_dialog = None


def open_editor() -> None:
    global _dialog
    if _dialog is None:
        _dialog = EditorDialog(mw)
    _dialog.refresh()
    _dialog.show()
    _dialog.raise_()
    _dialog.activateWindow()


def _install() -> None:
    action = QAction("Exam Timeline", mw)
    qconnect(action.triggered, open_editor)
    mw.form.menuTools.addAction(action)


gui_hooks.main_window_did_init.append(_install)
gui_hooks.webview_will_set_content.append(on_webview_content)
gui_hooks.webview_did_receive_js_message.append(on_js_message)

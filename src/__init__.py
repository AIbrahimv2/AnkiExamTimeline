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
.et-wrap { padding: 4px 6px 10px; font-family: -apple-system, system-ui, sans-serif;
           color: var(--fg, #1a1a1a); text-align: left; }
.et-head { display: flex; align-items: center; gap: 10px; margin: 0 0 12px; }
.et-head .et-title { font-size: 15px; font-weight: 700; letter-spacing: .01em; }
.et-head .et-sub { font-size: 12px; opacity: .5; }
.et-head .et-edit { margin-left: auto; font-size: 12px; font-weight: 600; color: #3b82f6;
                    background: transparent; border: none; cursor: pointer; padding: 3px 6px;
                    border-radius: 7px; }
.et-head .et-edit:hover { background: rgba(59,130,246,.12); }
.et-timeline { position: relative; display: flex; gap: 26px; overflow-x: auto;
               padding: 4px 2px 30px; align-items: flex-start; }
.et-line { position: absolute; left: 4px; right: 4px; bottom: 42px; height: 2px;
           background: var(--border, #d6d6d6); z-index: 0; }
.et-item { position: relative; z-index: 1; display: flex; flex-direction: column;
           align-items: center; min-width: 128px; }
.et-card { background: var(--canvas-elevated, #fff); border: 1px solid var(--border, #e2e2e2);
           border-radius: 15px; padding: 15px 18px 13px; text-align: center; min-width: 116px;
           box-shadow: 0 5px 16px rgba(0,0,0,0.10); }
.et-count { font-size: 48px; font-weight: 800; line-height: 1; letter-spacing: -.02em; }
.et-unit { font-size: 10px; text-transform: uppercase; letter-spacing: .07em; opacity: .55;
           margin-top: 4px; }
.et-name { font-size: 14px; font-weight: 600; margin-top: 11px; word-break: break-word; }
.et-date { font-size: 11px; opacity: .5; margin-top: 3px; }
.et-dot { width: 14px; height: 14px; border-radius: 50%; background: #3b82f6;
          border: 3px solid var(--canvas, #fff); margin-top: 18px; }
.et-item.near .et-count, .et-item.near .et-name { color: #f59e0b; }
.et-item.near .et-dot { background: #f59e0b; }
.et-item.soon .et-count, .et-item.soon .et-name { color: #ef4444; }
.et-item.soon .et-dot { background: #ef4444; }
.et-empty { opacity: .55; font-size: 13px; padding: 6px 2px 14px; }
.et-empty a { color: #3b82f6; cursor: pointer; text-decoration: none; }
.et-empty a:hover { text-decoration: underline; }
</style>
"""


def _urgency(d: int) -> str:
    return "soon" if d <= 7 else ("near" if d <= 30 else "")


def _timeline_card(exam: dict, d: int) -> str:
    name = _html.escape(exam.get("name", ""))
    iso = _html.escape(exam.get("date", ""))
    big = "0" if d == 0 else str(d)
    unit = "today" if d == 0 else ("day left" if d == 1 else "days left")
    return f"""
      <div class="et-item {_urgency(d)}">
        <div class="et-card">
          <div class="et-count">{big}</div>
          <div class="et-unit">{unit}</div>
          <div class="et-name">{name}</div>
          <div class="et-date">{iso}</div>
        </div>
        <div class="et-dot"></div>
      </div>
    """


def build_timeline_widget(exams: list) -> str:
    rows = upcoming(exams)
    n = len(rows)
    sub = "" if n == 0 else f'<span class="et-sub">{n} upcoming</span>'
    out = ['<div class="et-wrap">']
    out.append(
        '<div class="et-head"><span class="et-title">Exam Timeline</span>'
        f"{sub}"
        f"<button class=\"et-edit\" onclick=\"pycmd('{OPEN_CMD}')\">Edit</button></div>"
    )
    if not rows:
        out.append(
            '<div class="et-empty">No upcoming exams — '
            f"<a onclick=\"pycmd('{OPEN_CMD}')\">add one</a>.</div>"
        )
    else:
        out.append('<div class="et-timeline"><div class="et-line"></div>')
        out.extend(_timeline_card(e, d) for e, d in rows)
        out.append("</div>")
    out.append("</div>")
    out.append(TIMELINE_STYLE)
    return "".join(out)


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

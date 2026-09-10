# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""Exam Timeline — a horizontal countdown timeline of upcoming exams for Anki.

Tools -> Exam Timeline opens a window showing each upcoming exam left-to-right
on a timeline with a large "days left" countdown. Exams are added/removed from
an inline form and stored in the add-on config.
"""

from __future__ import annotations

import html as _html
import json
import time
from datetime import date

from aqt import gui_hooks, mw
from aqt.qt import QAction, QDialog, QVBoxLayout, qconnect
from aqt.utils import restoreGeom, saveGeom
from aqt.webview import AnkiWebView

GEOM_KEY = "exam_timeline"


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


# --- rendering ---------------------------------------------------------------

STYLE = """
<style>
.et-wrap { padding: 22px 26px 44px; font-family: -apple-system, system-ui, sans-serif;
           color: var(--fg, #1a1a1a); }
.et-head { display:flex; align-items:baseline; gap:10px; margin: 0 0 18px; }
.et-head h1 { font-size: 22px; font-weight: 700; margin: 0; }
.et-head .et-sub { font-size: 13px; opacity: .55; }
.et-form { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom: 30px; }
.et-in { padding: 9px 11px; border-radius: 9px; border: 1px solid var(--border, #ccc);
         background: var(--canvas-elevated, #fff); color: var(--fg, #000); font-size: 14px; }
#et-name { flex: 1; min-width: 200px; }
.et-add { padding: 9px 18px; border: none; border-radius: 9px; background: #3b82f6;
          color: #fff; font-weight: 600; cursor: pointer; font-size: 14px; }
.et-add:hover { background: #2563eb; }
.et-empty { opacity: .55; padding: 48px 0; text-align: center; font-size: 15px; }

.et-timeline { position: relative; display: flex; gap: 30px; overflow-x: auto;
               padding: 6px 4px 34px; align-items: flex-start; }
.et-line { position: absolute; left: 6px; right: 6px; bottom: 46px; height: 2px;
           background: var(--border, #d6d6d6); z-index: 0; }
.et-item { position: relative; z-index: 1; display: flex; flex-direction: column;
           align-items: center; min-width: 148px; }
.et-card { position: relative; background: var(--canvas-elevated, #fff);
           border: 1px solid var(--border, #e2e2e2); border-radius: 16px;
           padding: 18px 20px 15px; text-align: center; min-width: 128px;
           box-shadow: 0 6px 18px rgba(0,0,0,0.10); }
.et-count { font-size: 56px; font-weight: 800; line-height: 1; letter-spacing: -.02em; }
.et-unit { font-size: 11px; text-transform: uppercase; letter-spacing: .07em; opacity: .55;
           margin-top: 5px; }
.et-name { font-size: 15px; font-weight: 600; margin-top: 12px; word-break: break-word; }
.et-date { font-size: 12px; opacity: .5; margin-top: 3px; }
.et-dot { width: 15px; height: 15px; border-radius: 50%; background: #3b82f6;
          border: 3px solid var(--canvas, #fff); margin-top: 20px; }
.et-item.near .et-count, .et-item.near .et-name { color: #f59e0b; }
.et-item.near .et-dot { background: #f59e0b; }
.et-item.soon .et-count, .et-item.soon .et-name { color: #ef4444; }
.et-item.soon .et-dot { background: #ef4444; }
.et-del { position: absolute; top: 7px; right: 9px; border: none; background: transparent;
          color: var(--fg, #888); opacity: .3; font-size: 17px; line-height: 1; cursor: pointer; }
.et-del:hover { opacity: 1; color: #ef4444; }
</style>
"""

SCRIPT = """
<script>
function etAdd() {
  var n = document.getElementById('et-name').value.trim();
  var d = document.getElementById('et-date').value;
  if (!n || !d) { return; }
  pycmd('add:' + JSON.stringify({name: n, date: d}));
}
function etDel(id) { pycmd('del:' + id); }
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && (e.target.id === 'et-name' || e.target.id === 'et-date')) etAdd();
});
</script>
"""


def _card(exam: dict, d: int) -> str:
    name = _html.escape(exam.get("name", ""))
    iso = _html.escape(exam.get("date", ""))
    eid = _html.escape(str(exam.get("id", "")))
    urg = "soon" if d <= 7 else ("near" if d <= 30 else "")
    big = "0" if d == 0 else str(d)
    unit = "today" if d == 0 else ("day left" if d == 1 else "days left")
    return f"""
      <div class="et-item {urg}">
        <div class="et-card">
          <button class="et-del" title="Remove" onclick="etDel('{eid}')">&times;</button>
          <div class="et-count">{big}</div>
          <div class="et-unit">{unit}</div>
          <div class="et-name">{name}</div>
          <div class="et-date">{iso}</div>
        </div>
        <div class="et-dot"></div>
      </div>
    """


def build_body(exams: list) -> str:
    rows = []
    for e in exams:
        d = days_left(e.get("date", ""))
        if d is not None and d >= 0:
            rows.append((e, d))
    rows.sort(key=lambda x: x[1])

    n = len(rows)
    sub = "No upcoming exams" if n == 0 else (f"{n} upcoming exam" + ("" if n == 1 else "s"))
    out = ['<div class="et-wrap">']
    out.append(f'<div class="et-head"><h1>Exam Timeline</h1><span class="et-sub">{sub}</span></div>')
    out.append(
        '<div class="et-form">'
        '<input id="et-name" class="et-in" placeholder="Exam name (e.g. USMLE Step 1)" />'
        '<input id="et-date" class="et-in" type="date" />'
        '<button class="et-add" onclick="etAdd()">Add exam</button>'
        "</div>"
    )
    if not rows:
        out.append('<div class="et-empty">No upcoming exams yet — add one above.</div>')
    else:
        out.append('<div class="et-timeline"><div class="et-line"></div>')
        out.extend(_card(e, d) for e, d in rows)
        out.append("</div>")
    out.append("</div>")
    out.append(STYLE)
    out.append(SCRIPT)
    return "".join(out)


# --- dialog ------------------------------------------------------------------


class TimelineDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Exam Timeline")
        self.resize(920, 480)
        restoreGeom(self, GEOM_KEY)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.web = AnkiWebView(self, title="exam_timeline")
        self.web.set_bridge_command(self._on_cmd, self)
        layout.addWidget(self.web)

    def refresh(self) -> None:
        self.web.stdHtml(build_body(get_config()["exams"]))

    def _on_cmd(self, cmd: str):
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
                self.refresh()
        elif cmd.startswith("del:"):
            rid = cmd[4:]
            cfg = get_config()
            cfg["exams"] = [e for e in cfg["exams"] if str(e.get("id")) != rid]
            save_config(cfg)
            self.refresh()
        return None

    def closeEvent(self, ev) -> None:
        saveGeom(self, GEOM_KEY)
        super().closeEvent(ev)


_dialog = None


def open_dialog() -> None:
    global _dialog
    if _dialog is None:
        _dialog = TimelineDialog(mw)
    _dialog.refresh()
    _dialog.show()
    _dialog.raise_()
    _dialog.activateWindow()


def _install() -> None:
    action = QAction("Exam Timeline", mw)
    qconnect(action.triggered, open_dialog)
    mw.form.menuTools.addAction(action)


gui_hooks.main_window_did_init.append(_install)

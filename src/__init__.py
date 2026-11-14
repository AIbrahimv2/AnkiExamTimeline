# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""Exam Timeline — a horizontal countdown timeline of upcoming exams for Anki.

A read-only timeline widget is shown on the deck browser (home) screen with a
large "days left" countdown per exam. Exams are added and removed from a
separate editor window (Tools -> Exam Timeline, or the gear button on the
widget), a web page in editor.py. Data is stored in the add-on config.
"""

from __future__ import annotations

import json
from datetime import date

from aqt import gui_hooks, mw
from aqt.qt import QAction, qconnect

from . import kit
from .editor import open_editor
from .exams import ConfigStore, upcoming

OPEN_CMD = "examtl:open"


def get_config() -> dict:
    return ConfigStore(__name__).load()


# --- timeline widget (deck browser) ------------------------------------------

TIMELINE_STYLE = """
<style>
.et-wrap { box-sizing: border-box; width: 500px; max-width: 100%; margin: 30px auto 12px;
           padding: 6px 10px 0; text-align: left;
           font-family: -apple-system, system-ui, sans-serif; color: var(--fg, #1a1a1a); }
.et-focus { text-align: center; }
.et-hero { flex: 1; text-align: center; padding: 4px 0 2px; min-width: 0; }
.et-count { font-size: 76px; font-weight: 800; line-height: .95; letter-spacing: -.03em;
            color: var(--fg, #1a1a1a); }
.et-unit { font-size: 12px; text-transform: uppercase; letter-spacing: .1em; opacity: .55;
           margin-top: 2px; }
.et-name { font-size: 19px; font-weight: 700; margin-top: 12px; word-break: break-word; }
.et-date { font-size: 13px; opacity: .55; margin-top: 3px; }

.et-track { position: relative; height: 30px; margin: 14px 14px 0; }
.et-rail { position: absolute; left: 0; right: 0; top: 13px; height: 2px;
           background: var(--border, #e0e0e0); }
.et-tick { position: absolute; top: 13px; transform: translate(-50%, -50%); width: 10px;
           height: 10px; border-radius: 50%; background: var(--border, #c4c4c4);
           border: 2px solid var(--canvas, #fff); cursor: pointer;
           transition: width .15s, height .15s, background .15s, box-shadow .15s; }
.et-tick:hover { background: #9aa0a6; }
.et-tick.active { width: 16px; height: 16px; background: var(--fg, #555);
                  box-shadow: 0 0 0 4px rgba(127,127,127,.2); }
.et-counter { display: flex; align-items: center; justify-content: center; gap: 7px;
              margin-top: 5px; }
.et-count-text { font-size: 11px; letter-spacing: .05em; opacity: .4; }
.et-gear { flex: none; box-sizing: border-box; width: 22px; height: 22px; padding: 0;
           border: none; background: transparent; color: var(--fg, #888); opacity: .35;
           cursor: pointer; line-height: 0; border-radius: 6px;
           display: inline-flex; align-items: center; justify-content: center;
           transition: opacity .15s, background .15s; }
.et-gear:hover { opacity: .9; background: rgba(127,127,127,.14); }

.et-empty { opacity: .55; font-size: 13px; padding: 14px 2px; }
.et-empty a { color: var(--fg, #1a1a1a); cursor: pointer; text-decoration: underline; }
.et-empty a:hover { opacity: .7; }
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
  var countEl = root.querySelector('.et-count');
  var unitEl = root.querySelector('.et-unit');
  var nameEl = root.querySelector('.et-name');
  var dateEl = root.querySelector('.et-date');
  var counterEl = root.querySelector('.et-count-text');
  var track = root.querySelector('.et-track');
  var ticks = [];
  Array.prototype.forEach.call(track.querySelectorAll('.et-tick'), function (t) { t.remove(); });

  function posPct(d) { return EXAMS.length === 1 ? 50 : (6 + (d / maxDays) * 88); }

  EXAMS.forEach(function (e, i) {
    var t = document.createElement('div');
    t.className = 'et-tick';
    t.style.left = posPct(e.days) + '%';
    t.title = e.name + ' \\u2014 ' + e.pretty;
    t.addEventListener('click', function () { focus = i; render(); });
    track.appendChild(t);
    ticks.push(t);
  });

  function render() {
    var e = EXAMS[focus];
    countEl.textContent = e.days === 0 ? '0' : String(e.days);
    unitEl.textContent = e.days === 0 ? 'today' : (e.days === 1 ? 'day left' : 'days left');
    nameEl.textContent = e.name;
    dateEl.textContent = e.pretty;
    counterEl.textContent = (focus + 1) + ' / ' + EXAMS.length;
    ticks.forEach(function (t, i) {
      t.className = 'et-tick' + (i === focus ? ' active' : '');
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') { return; }
    var t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) { return; }
    if (EXAMS.length < 2) { return; }
    e.preventDefault();
    focus = (focus + (e.key === 'ArrowRight' ? 1 : -1) + EXAMS.length) % EXAMS.length;
    render();
  });
  render();
})();
</script>
"""

# Some add-ons (e.g. Memory Forest, Ankimon) *prepend* to the same area we
# append to, so hook order alone can't keep us on top. Instead the widget lifts
# itself to sit directly under the deck list (home) or counts table (overview).
PLACE_SCRIPT = """
<script>
(function () {
  var wrap = document.getElementById('et-widget');
  var anchor = document.getElementById('study') || document.querySelector('.decktd');
  var table = anchor && anchor.closest('table');
  if (wrap && table) { table.parentNode.insertBefore(wrap, table.nextSibling); }
})();
</script>
"""


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


GEAR_SVG = (
    "<svg viewBox='0 0 24 24' width='13' height='13' fill='currentColor' aria-hidden='true'>"
    "<path d='M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14."
    "23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94"
    "l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13."
    "57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-."
    "05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29."
    "59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-."
    "41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-."
    "47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 "
    "3.6-1.62 3.6-3.6 3.6z'/></svg>"
)


def _gear() -> str:
    return (
        f"<button class=\"et-gear\" onclick=\"pycmd('{OPEN_CMD}')\" "
        f'aria-label="Edit exams" title="Edit exams">{GEAR_SVG}</button>'
    )


def build_timeline_widget(exams: list) -> str:
    data = _widget_data(exams)
    if not data:
        return (
            '<div class="et-wrap" id="et-widget"><div class="et-empty">No upcoming exams — '
            f"<a onclick=\"pycmd('{OPEN_CMD}')\">add one</a>.</div></div>"
            f"{TIMELINE_STYLE}{PLACE_SCRIPT}"
        )
    body = (
        '<div class="et-wrap" id="et-widget">'
        '<div class="et-focus">'
        '<div class="et-hero"><div class="et-count"></div><div class="et-unit"></div>'
        '<div class="et-name"></div><div class="et-date"></div></div>'
        "</div>"
        '<div class="et-track"><div class="et-rail"></div></div>'
        f'<div class="et-counter"><span class="et-count-text"></span>{_gear()}</div>'
        "</div>"
    )
    payload = json.dumps(data).replace("</", "<\\/")
    return body + TIMELINE_STYLE + PLACE_SCRIPT + WIDGET_SCRIPT.replace("__DATA__", payload)


def on_deck_render(deck_browser, content) -> None:
    """Insert the read-only timeline into the deck screen's stats area; it then
    moves itself directly under the deck list, above every other add-on."""
    content.stats += build_timeline_widget(get_config()["exams"])


def on_overview_render(overview, content) -> None:
    """Insert the timeline into the deck overview; it then moves itself directly
    under the counts table, above every other add-on."""
    content.table += build_timeline_widget(get_config()["exams"])


def on_js_message(handled, message: str, context):
    if message == OPEN_CMD:
        open_editor()
        return (True, None)
    return handled


def _install() -> None:
    action = QAction("Exam Timeline", mw)
    qconnect(action.triggered, open_editor)
    mw.form.menuTools.addAction(action)


# The editor's page loads its built script and styles from /_addons/<folder>/web/.
mw.addonManager.setWebExports(__name__, r"web/.*\.(js|css)")


def _register_first(hook, cb) -> None:
    """Register a render hook so it runs *before* other add-ons that append to
    the same area (e.g. Review Heatmap). Running first means our widget is
    appended right after the stats/counts and the heatmap lands below it,
    regardless of add-on load order. PLACE_SCRIPT does the final positioning;
    this keeps the order sensible if it can't find its anchor."""
    hooks = getattr(hook, "_hooks", None)
    if isinstance(hooks, list):
        hooks.insert(0, cb)
    else:
        hook.append(cb)


gui_hooks.main_window_did_init.append(_install)
_register_first(gui_hooks.deck_browser_will_render_content, on_deck_render)
_register_first(gui_hooks.overview_will_render_content, on_overview_render)
gui_hooks.webview_did_receive_js_message.append(on_js_message)
# The add-on kit shared with AIbrahimv2's other add-ons (src/kit/): What's new
# and About in the editor's ⋯ menu, and one notice after updates.
kit.register("exam-timeline")

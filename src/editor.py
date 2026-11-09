# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""The editor window: the web UI (React, built from web/ into src/web/) in an
AnkiWebView, talking to bridge.Bridge over pycmd.

The page never uses <input type="date"> or other controls that open a native
popup: in Anki's web view on macOS those crash Anki. The date picker is drawn
by the page itself.
"""

from __future__ import annotations

import os

from aqt import mw
from aqt.qt import QDialog, QVBoxLayout
from aqt.utils import restoreGeom, saveGeom
from aqt.webview import AnkiWebView

from .bridge import Bridge
from .exams import ConfigStore

GEOM_KEY = "exam_timeline_web"
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


def addon_folder() -> str:
    return mw.addonManager.addonFromModule(__name__)


def asset_url(name: str) -> str:
    """A built asset's URL, versioned by mtime so a rebuild is never cached."""
    try:
        v = int(os.path.getmtime(os.path.join(WEB_DIR, name)))
    except OSError:
        v = 0
    return f"/_addons/{addon_folder()}/web/{name}?v={v}"


def refresh_widget() -> None:
    """Redraw the deck screen's timeline after a change."""
    if mw.state == "deckBrowser":
        mw.deckBrowser.refresh()
    elif mw.state == "overview":
        mw.overview.refresh()


class EditorDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Exam Timeline")
        self.setMinimumSize(380, 420)
        self.resize(560, 640)
        restoreGeom(self, GEOM_KEY)

        self.bridge = Bridge(ConfigStore(__name__), on_change=refresh_widget)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.web = AnkiWebView(self, title="exam_timeline")
        self.web.set_bridge_command(self.bridge.handle, self)
        lay.addWidget(self.web)
        self.web.stdHtml(
            '<div id="root"></div>',
            css=[asset_url("app.css")],
            js=[asset_url("app.js")],
            context=self,
        )

    def reload_exams(self) -> None:
        """The page asks for the list again (the window was reopened)."""
        self.web.eval("window.examTimeline && window.examTimeline.reload();")

    def closeEvent(self, ev) -> None:
        saveGeom(self, GEOM_KEY)
        super().closeEvent(ev)

    def reject(self) -> None:
        saveGeom(self, GEOM_KEY)
        super().reject()


_dialog: EditorDialog | None = None


def open_editor() -> None:
    global _dialog
    if _dialog is None:
        _dialog = EditorDialog(mw)
    else:
        _dialog.reload_exams()
    _dialog.show()
    _dialog.raise_()
    _dialog.activateWindow()
    _dialog.web.setFocus()

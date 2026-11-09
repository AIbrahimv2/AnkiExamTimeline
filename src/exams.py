# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""The exam list: stored in the add-on's config, and the date maths shared by
the deck-screen widget and the editor."""

from __future__ import annotations

from datetime import date


def days_left(iso: str, today: date | None = None):
    try:
        return (date.fromisoformat(iso) - (today or date.today())).days
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


class ConfigStore:
    """The exams in Anki's add-on config."""

    def __init__(self, module: str):
        self.module = module

    def load(self) -> dict:
        from aqt import mw

        cfg = mw.addonManager.getConfig(self.module) or {}
        if not isinstance(cfg.get("exams"), list):
            cfg["exams"] = []
        return cfg

    def save(self, cfg: dict) -> None:
        from aqt import mw

        mw.addonManager.writeConfig(self.module, cfg)

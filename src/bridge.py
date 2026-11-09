# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""Commands from the editor page (web/ -> src/web/), as JSON over pycmd.

Plain Python with no Anki imports, so tests and tools/devserver.py can run the
exact same code against a JSON file. Every reply carries the full exam list,
so the page never has to patch its copy.
"""

from __future__ import annotations

import json
import time
from datetime import date
from typing import Callable, Protocol

MAX_NAME = 80


class Store(Protocol):
    def load(self) -> dict: ...

    def save(self, cfg: dict) -> None: ...


class Bridge:
    def __init__(self, store: Store, on_change: Callable[[], None] = lambda: None,
                 today: Callable[[], date] = date.today):
        self.store = store
        self.on_change = on_change
        self.today = today

    # --- plumbing --------------------------------------------------------------

    def handle(self, raw: str) -> dict:
        try:
            msg = json.loads(raw)
            fn = getattr(self, f"cmd_{msg.get('cmd')}", None)
            if fn is None:
                return {"error": f"Unknown command: {msg.get('cmd')}"}
            return fn(msg)
        except ValueError as e:
            return {"error": str(e)}

    def _exams(self) -> list[dict]:
        return [e for e in self.store.load()["exams"] if isinstance(e, dict)]

    def _save(self, exams: list[dict]) -> None:
        cfg = self.store.load()
        cfg["exams"] = exams
        self.store.save(cfg)
        self.on_change()

    def _state(self, **extra) -> dict:
        return {"exams": self._exams(), "today": self.today().isoformat(), **extra}

    @staticmethod
    def _name(msg: dict) -> str:
        name = " ".join(str(msg.get("name", "")).split())
        if not name:
            raise ValueError("Give the exam a name.")
        return name[:MAX_NAME]

    @staticmethod
    def _date(msg: dict) -> str:
        iso = str(msg.get("date", ""))
        try:
            return date.fromisoformat(iso).isoformat()
        except ValueError:
            raise ValueError("Pick a date for the exam.") from None

    def _new_id(self, exams: list[dict]) -> int:
        taken = {str(e.get("id")) for e in exams}
        new = int(time.time() * 1000)
        while str(new) in taken:
            new += 1
        return new

    # --- commands --------------------------------------------------------------

    def cmd_load(self, msg: dict) -> dict:
        return self._state()

    def cmd_add(self, msg: dict) -> dict:
        exams = self._exams()
        exam = {"id": self._new_id(exams), "name": self._name(msg), "date": self._date(msg)}
        self._save(exams + [exam])
        return self._state(added=exam["id"])

    def cmd_update(self, msg: dict) -> dict:
        rid = str(msg.get("id"))
        exams = self._exams()
        hit = next((e for e in exams if str(e.get("id")) == rid), None)
        if hit is None:
            raise ValueError("That exam is gone; it may have been removed.")
        hit.update(name=self._name(msg), date=self._date(msg))
        self._save(exams)
        return self._state()

    def cmd_remove(self, msg: dict) -> dict:
        rid = str(msg.get("id"))
        exams = self._exams()
        removed = next((e for e in exams if str(e.get("id")) == rid), None)
        self._save([e for e in exams if str(e.get("id")) != rid])
        return self._state(removed=removed)

    def cmd_restore(self, msg: dict) -> dict:
        """Put back an exam just removed (the toast's Undo)."""
        exam = msg.get("exam")
        if not isinstance(exam, dict):
            raise ValueError("Nothing to put back.")
        exams = self._exams()
        if any(str(e.get("id")) == str(exam.get("id")) for e in exams):
            return self._state()
        restored = {"id": exam.get("id") or self._new_id(exams), "name": self._name(exam), "date": self._date(exam)}
        self._save(exams + [restored])
        return self._state()

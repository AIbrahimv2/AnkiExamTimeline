#!/usr/bin/env bash
# Run all the tests: the date reading (Node), the editor's commands (Python)
# and the editor itself in Anki's web view (Anki's own Python).
set -uo pipefail
cd "$(dirname "$0")/.."

PY="${ANKI_PYTHON:-}"
if [ -z "$PY" ]; then
  for p in "$HOME"/Library/Application\ Support/AnkiProgramFiles/python/*/bin/python3; do PY="$p"; done
fi

failed=0
run() {
  local name="$1"; shift
  local out code
  out="$(timeout 300 "$@" 2>&1)"
  code=$?
  if [ "$code" -eq 0 ]; then
    echo "ok    $name"
  else
    echo "FAIL  $name (exit $code)"
    echo "$out" | grep -v "Fontconfig\|propagateSizeHints\|does not support raise\|ERROR:\|SKIA" | tail -25
    failed=$((failed + 1))
  fi
}

run dates node --test tests/dates.test.ts
run bridge python3 tests/test_bridge.py
if [ -x "$PY" ]; then
  run webview "$PY" tests/test_webview.py
else
  echo "skip  webview (Anki's Python not found: set ANKI_PYTHON)"
fi

echo
[ "$failed" -eq 0 ] && echo "All passed" || { echo "$failed failed"; exit 1; }

# Notes for agents

Exam Timeline is one of AIbrahimv2's Anki add-ons (AnkiWeb ID 341595498).

To release it, publish it, or edit its AnkiWeb listing, follow the
`anki-addon-release` skill. It covers all of the user's add-ons: the
changelog, building and checking the package, the GitHub release, AnkiWeb, the
listing and AnkiWeb search.

- **On the user's Mac** it loads by itself, from
  `~/.claude/skills/anki-addon-release`.
- **Anywhere else**, such as a cloud session, read it first:
  https://github.com/AIbrahimv2/AnkiStepwise/tree/main/.claude/skills/anki-addon-release
  (`SKILL.md`, and `scripts/` for the package and search checks).

This repo: `./build.sh` builds the editor's web UI (`web/` into `src/web/`)
and then `dist/anki-exam-timeline.ankiaddon` from `src/`. `./tests/run.sh` runs
the tests. Never use `<input type="date">`, `<select>` or other native-popup
controls in the editor page: they crash Anki's web view on macOS.
The AnkiWeb listing (title, tags, versions, description) is in
`docs/ankiweb-listing.md`. Keep it matching what's live.

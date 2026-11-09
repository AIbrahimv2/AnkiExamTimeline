# Exam Timeline

An [Anki](https://apps.ankiweb.net/) add-on that shows your upcoming exams on a
horizontal countdown timeline. Each exam appears as a card with a large
"days left" number, sorted so the nearest exam is first.

<img width="1800" height="1169" alt="Screenshot 2026-10-06 at 12 18 54" src="https://github.com/user-attachments/assets/aaae8840-53d6-4c34-b3b0-f63387a095a1" />

## Features

- **Timeline widget** on the deck (home) and deck-overview screens showing
  upcoming exams, nearest first, each with a **large day countdown**. Use the
  **← / →** arrow keys to step through exams.
- **Separate editor window** for adding, editing and removing exams — the
  widget itself stays read-only.
- **Type dates the way you'd say them**: "Nov 20", "11/20", "next friday",
  "in 3 weeks". The field spells out the date it understood and how far away it
  is, so a typo can't slip through. Or pick it from the calendar, which marks
  the days you already have exams on and has quick picks (1 week, 1 month, …).
- Removed an exam by mistake? **Undo** puts it back.
- Exams **persist** between sessions and past exams are hidden from the widget
  automatically.

## Usage

The timeline appears on the deck and deck-overview screens. To manage exams, open
**Tools → Exam Timeline** (or click the **gear** next to the countdown): type a name
and a date, and press **Enter** or click **Add exam**. Hover over an exam to edit
it (pencil) or remove it (**×**). Changes appear on the deck screen immediately.

Clicking in the date field opens the calendar, which follows what you type; **↓**
moves into it. There, the arrow keys move a day or a week, **Page Up / Page Down** a month (with **Shift**, a year), **Enter** picks the
day and **Esc** closes it.

## Installation

### From AnkiWeb

Search for "Exam Timeline" in Anki's **Tools → Add-ons → Get Add-ons**.

### Manual

Download `anki-exam-timeline.ankiaddon` from the
[Releases](https://github.com/AIbrahimv2/AnkiExamTimeline/releases) page and
double-click it, or run `./build.sh` and open the file it writes to `dist/`.

## Development

The add-on lives in `src/`. The editor window is a small React app in `web/`,
built into `src/web/` (the built files are committed, so `src/` works as is).
To test changes live, symlink `src/` into your Anki add-ons folder and restart
Anki:

```bash
ln -s "$(pwd)/src" ~/Library/Application\ Support/Anki2/addons21/anki-exam-timeline
```

- `npm --prefix web run build` rebuilds the editor after changes in `web/`.
- `python3 tools/devserver.py --exams src/meta.json` runs the editor in a
  browser at http://127.0.0.1:5181, against the add-on's real Python commands
  and a copy of your exams (`npm --prefix web run dev` for live reload).
- `./tests/run.sh` runs the tests: date reading (Node), the editor's commands
  (Python) and the editor in Anki's own web view (Anki's Python).
- `./build.sh` builds the editor and writes a distributable `.ankiaddon` to
  `dist/`.

Never use `<input type="date">`, `<select>` or other controls with a native
popup in the editor: in Anki's web view on macOS they crash Anki.

## License

[AGPL-3.0-or-later](LICENSE).

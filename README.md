# Exam Timeline

An [Anki](https://apps.ankiweb.net/) add-on that shows your upcoming exams on a
horizontal countdown timeline. Each exam appears as a card with a large
"days left" number, sorted so the nearest exam is first.

<img width="1800" height="1169" alt="Screenshot 2026-10-06 at 12 18 54" src="https://github.com/user-attachments/assets/aaae8840-53d6-4c34-b3b0-f63387a095a1" />

## Features

- **Timeline widget** on the deck (home) and deck-overview screens showing
  upcoming exams, nearest first, each with a **large day countdown**. Use the
  **← / →** arrow keys to step through exams.
- **Separate editor window** for entering and removing exams — the widget itself
  stays read-only.
- Exams **persist** between sessions and past exams are hidden from the widget
  automatically.

## Usage

The timeline appears on the deck and deck-overview screens. To manage exams, open
**Tools → Exam Timeline** (or click the **gear** next to the countdown): type a name, pick a
date, and click **Add exam**. Remove an exam with the **×** on its row. Changes
appear on the deck screen immediately.

## Installation

### From AnkiWeb

Search for "Exam Timeline" in Anki's **Tools → Add-ons → Get Add-ons**.

### Manual

Download `anki-exam-timeline.ankiaddon` from the
[Releases](https://github.com/AIbrahimv2/AnkiExamTimeline/releases) page and
double-click it, or run `./build.sh` and open the file it writes to `dist/`.

## Development

The add-on lives entirely in `src/`. To test changes live, symlink `src/` into
your Anki add-ons folder and restart Anki:

```bash
ln -s "$(pwd)/src" ~/Library/Application\ Support/Anki2/addons21/anki-exam-timeline
```

Run `./build.sh` to produce a distributable `.ankiaddon` in `dist/`.

## License

[AGPL-3.0-or-later](LICENSE).

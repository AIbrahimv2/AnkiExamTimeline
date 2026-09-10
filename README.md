# Exam Timeline

An [Anki](https://apps.ankiweb.net/) add-on that shows your upcoming exams on a
horizontal countdown timeline. Each exam appears as a card with a large
"days left" number, sorted so the nearest exam is first, and colour-coded by
urgency (red within a week, amber within a month).

## Features

- **Horizontal timeline** of upcoming exams, nearest first.
- **Large day countdown** per exam.
- **Easy entry** — an inline form (name + date) adds an exam; a per-card button
  removes one.
- Exams **persist** between sessions and past exams are hidden automatically.

## Usage

Open **Tools → Exam Timeline**. Type an exam name, pick a date, and click
**Add exam**. Remove an exam with the **×** on its card.

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

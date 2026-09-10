# Exam Timeline

An [Anki](https://apps.ankiweb.net/) add-on that shows your upcoming exams on a
horizontal countdown timeline. Each exam appears as a card with a large
"days left" number, sorted so the nearest exam is first, and colour-coded by
urgency (red within a week, amber within a month).

## Features

- **Timeline widget** on the deck (home) screen showing upcoming exams, nearest
  first, each with a **large day countdown**.
- **Separate editor window** for entering and removing exams — the widget itself
  stays read-only.
- Exams **persist** between sessions and past exams are hidden from the widget
  automatically.

## Usage

The timeline appears at the top of the deck screen. To manage exams, open
**Tools → Exam Timeline** (or click **Edit** on the widget): type a name, pick a
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

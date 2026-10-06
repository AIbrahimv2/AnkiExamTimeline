# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-10-06

### Added

- Initial release.
- Read-only **timeline widget** on the deck (home) and deck-overview screens,
  focused on one exam at a time with a large "days left" countdown. Step
  through exams with the **← / →** arrow keys.
- Separate **editor window** (Tools → Exam Timeline, or the gear next to the
  countdown) to add and remove exams using a native date picker; changes
  update the widget immediately.
- Exams persist in the add-on config; past exams are hidden from the widget
  automatically.

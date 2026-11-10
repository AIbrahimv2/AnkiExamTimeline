# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- The editor window is redesigned. Exams show with their countdown, upcoming
  first, with past exams folded away underneath.
- A new date field: type the date the way you'd say it ("Nov 20", "11/20",
  "next friday", "in 3 weeks") and the calendar, which opens with the field,
  shows it as you type, while the field says how far away it is or what's
  wrong ("November has only 30 days"). Or pick it in the calendar, which
  marks the days you already have exams on, jumps to any month or year from
  its title and works from the keyboard.

### Added

- Edit an exam's name or date in place.
- Removing an exam asks first.

### Fixed

- The timeline now always sits directly under the deck list (and under the
  counts table on the overview screen), above panels from other add-ons such as
  Memory Forest or Ankimon that insert themselves into the same area.

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

# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- About lists Skim with an Install button, now that it's on AnkiWeb.

- **Settings, What's new and About are one surface** from top to bottom: the
  header, the tabs and the Save and Close bar no longer sit on bands of their
  own. Only what's between them scrolls, and it fades out at its edges.

### Removed

- ⌘⇧E (Ctrl+Shift+E on Windows and Linux) no longer opens Exam Timeline,
  so it's free for Anki's editor when Skim takes `e`. Open it from
  **Tools → Exam Timeline**, or the gear next to the countdown.

## [1.3.0] - 2026-11-17

### Added

- **⌘⇧E opens Exam Timeline** (Ctrl+Shift+E on Windows and Linux), from
  anywhere in Anki's main window.
- **Liquid Glass with AnkiGlass.** On a Mac with AnkiGlass installed, the
  Exam Timeline window and its What's new and About window get the same
  glass as Anki's main window. **Glass on add-on windows** in AnkiGlass's
  Settings turns it off.

### Changed

- **What's new and About open in a window of their own**, wider and easier
  to read: each version's changes sit beside its number, and the other
  add-ons are laid out as cards.
- **The signature at the end of About signs itself**, stroke by stroke, as
  if written by hand when you scroll to it.
- Add-on emoji stand on their own now, without a box around them.
- About ends with links to AIbrahimv2's LinkedIn and Instagram, under the
  signature, and the signature opens AIbrahimv2's website.
- With no upcoming exams, the deck screen now shows a clear "Add an exam"
  button instead of a small link. After your last exam it says which one it
  was and how long ago, so you can add the next one.
- **On a Mac, ⌘, opens the settings of the add-on you're in.** With
  Stepwise's, Skim's or AnkiGlass's window in front, it opens that add-on's
  settings instead of Anki's Preferences. Everywhere else, Exam Timeline's
  window included, it still opens Anki's.

### Fixed

- Exams a few days apart, or on the same day, no longer pile up on the
  timeline: their dots sit side by side, so each one can be clicked. With
  lots of exams, the dots get smaller to fit.

## [1.2.0] - 2026-11-17

### Added

- **What's new and About**, in the editor's ⋯ menu: What's new (this list of
  changes, with the ones since you last looked marked New) and About (links
  to the code and to report a problem, whether AnkiWeb has an update, and
  AIbrahimv2's other Anki add-ons, with an Install button). A dot on ⋯ says
  there's an update you haven't read about.
- **One notice after updates.** When any of AIbrahimv2's add-ons is updated, a
  card at the bottom of Anki's main window says so once, with a link to
  what's new.

### Changed

- The editor's buttons and its "Remove this exam?" dialog look like the ones
  in AIbrahimv2's other add-ons.

## [1.1.0] - 2026-11-09

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

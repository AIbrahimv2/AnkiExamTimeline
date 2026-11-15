# AnkiWeb listing

What's live at https://ankiweb.net/shared/info/341595498. Edit it at
https://ankiweb.net/shared/upload?id=341595498, and update this file in the
same session.

## Title

📅 Exam Timeline: a countdown to your upcoming exams on the deck screen

## Tags

exam countdown timeline deadline study planner

## Support page

https://github.com/AIbrahimv2/AnkiExamTimeline/issues

## Supported Anki versions

Minimum 24.04, maximum 26.09.4 with no `-`, so newer versions get it too. The
form turns 24.04 into "24.04.0", and the listing shows "24.04-26.09.4+".

Anki says the code is invalid to anyone below the minimum. Until 2026-11-14
both were 26.09.4, the version installed at the time, so only 26.09.4 and
newer could install it. Checked after the change with
`curl -s -o /dev/null --max-filesize 1 -w '%{http_code}' "https://ankiweb.net/shared/download/341595498?v=2.1&p=<point version>"`:
404 for 2.1.66, 23.10 and 23.12.1 (p=66, 231000, 231201), and 303 (a
download) for 24.04 to 26.10 (240400 up).

Why 24.04:

- It's the first release whose Mac, Windows and Linux builds all ship Qt 6.6,
  whose web view is Chromium 112. The editor's stylesheet uses `color-mix()`,
  which needs Chromium 111, so on the Qt 6.5 builds (2.1.66, and 23.12 on
  Mac) most of its colours would be missing. Nothing else in the editor or the
  deck-screen widget needs a newer browser.
- Up to 25.02, Anki runs add-ons on Python 3.9. Exam Timeline works there.
- The deck-screen widget uses `deck_browser_will_render_content` and
  `overview_will_render_content` (their `stats` and `table` sections), which
  24.04 has.

Tested on 2026-11-14 with `tests/run_on_anki.sh <version>`. All the tests
(dates, bridge, and the editor in Anki's web view) pass on 24.04, 24.06.3,
24.11 and 25.02.7 (Python 3.9, Qt 6.6), 25.07.5 and 25.09.4 (Python 3.13, the
launcher's default Qt 6.9), and 26.09.4 (the installed app). The 1.1.0 code,
which is what AnkiWeb serves, passes on 24.04 and 25.07.5. Not tested: the
launcher's optional Qt 6.7 and 6.8 builds, which sit between versions that
pass. Rerun the tests on the minimum before each release.

## Description

Paste as is. AnkiWeb takes Markdown and basic HTML.

```html
<p><img alt="Screenshot 2026-10-06 at 12 18 54" src="https://github.com/user-attachments/assets/aaae8840-53d6-4c34-b3b0-f63387a095a1" /></p>
<b>Features</b>
<ul>
<li>A clean timeline widget on the <b>deck (home)</b> and <b>deck overview</b> screens, showing one exam at a time with a large <b>days left</b> number. The nearest exam comes first.</li>
<li>Press the <b>← / →</b> arrow keys to step through your exams.</li>
<li>Add, edit and remove exams in a separate editor window: <b>Tools → Exam Timeline</b>, or click the gear next to the countdown.</li>
<li>Type a date the way you'd say it ("Nov 20", "11/20", "next friday", "in 3 weeks"), or pick it in a calendar that marks the days you already have exams on.</li>
<li>Exams are saved between sessions, and past exams disappear on their own.</li>
</ul>

<b>Source, bug reports and changelog</b>
[github.com/AIbrahimv2/AnkiExamTimeline](https://github.com/AIbrahimv2/AnkiExamTimeline)
```

// The editor's date reading (web/src/dates.ts). Node runs TypeScript as is:
//   node --test tests/dates.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";
import { addMonths, dayDiff, explain, fromISO, parseLoose, relative, toISO } from "../web/src/dates.ts";

// Monday, November 9, 2026.
const TODAY = new Date(2026, 10, 9);
const read = (text: string) => {
  const d = parseLoose(text, TODAY);
  return d ? toISO(d) : null;
};

test("words and distances from today", () => {
  assert.equal(read("today"), "2026-11-09");
  assert.equal(read("Tomorrow"), "2026-11-10");
  assert.equal(read("next week"), "2026-11-16");
  assert.equal(read("next month"), "2026-12-09");
  assert.equal(read("next year"), "2027-11-09");
  assert.equal(read("in 3 weeks"), "2026-11-30");
  assert.equal(read("in 10 days"), "2026-11-19");
  assert.equal(read("+10"), "2026-11-19");
  assert.equal(read("2 months"), "2027-01-09");
  assert.equal(read("a week"), "2026-11-16");
  assert.equal(read("in 1 year"), "2027-11-09");
  assert.equal(read("3 weeks from now"), "2026-11-30");
});

test("weekdays mean the next one after today", () => {
  assert.equal(read("friday"), "2026-11-13");
  assert.equal(read("next fri"), "2026-11-13");
  assert.equal(read("monday"), "2026-11-16", "today is a Monday, so a week on");
  assert.equal(read("tue"), "2026-11-10");
});

test("month and day, either way round", () => {
  assert.equal(read("Nov 20"), "2026-11-20");
  assert.equal(read("november 20th"), "2026-11-20");
  assert.equal(read("20 nov"), "2026-11-20");
  assert.equal(read("20th of November 2027"), "2027-11-20");
  assert.equal(read("dec 31"), "2026-12-31");
  assert.equal(read("Fri, Nov 20, 2026"), "2026-11-20", "the field's own tidy format reads back");
  assert.equal(read("nov 1"), "2027-11-01", "a day that's passed means next year's");
  assert.equal(read("Jan 5"), "2027-01-05");
});

test("numbers", () => {
  assert.equal(read("2026-12-01"), "2026-12-01");
  assert.equal(read("11/20"), "2026-11-20");
  assert.equal(read("11/20/27"), "2027-11-20");
  assert.equal(read("1/5/2027"), "2027-01-05");
  assert.equal(read("10/12/"), "2027-10-12", "a separator left trailing mid-typing is fine");
  assert.equal(read("10/12/2026/"), "2026-10-12");
  assert.equal(read("oct 12,"), "2027-10-12");
  assert.equal(read("20"), "2026-11-20", "a day of the month alone is the next one");
  assert.equal(read("3"), "2026-12-03");
  assert.equal(read("9"), "2026-11-09");
});

test("what isn't a date", () => {
  for (const s of ["", "   ", "soon", "nov 31", "feb 30", "13/20", "in weeks", "mayday", "32", "10/12/2", "10/12/202"]) {
    assert.equal(read(s), null, s);
  }
});

test("why a date can't be read, in the style it was typed", () => {
  const why = (t: string) => explain(t, TODAY);
  assert.equal(why("nov 31"), "November has only 30 days.");
  assert.equal(why("fri nov 31"), "November has only 30 days.");
  assert.equal(why("31 april"), "April has only 30 days.");
  assert.equal(why("2/30"), "February has only 29 days.");
  assert.equal(why("2/29/2027"), "February 29 only comes in leap years.");
  assert.equal(why("feb 29 2027"), "February 29 only comes in leap years.");
  assert.equal(why("20/11"), "Put the month first: 11/20.");
  assert.equal(why("13/13"), "There are only 12 months.");
  assert.equal(why("10/12/2"), "Finish the year, like 10/12/2026.");
  assert.equal(why("oct 12 202"), "Finish the year, like Oct 12 2026.");
  assert.equal(why("10/12/x"), "Write it as month/day/year, like 10/12/2026.");
  assert.equal(why("32"), "Write it as month/day/year, like 10/12/2026.");
  assert.equal(why("soon"), "Try a date like Oct 12, next Friday or in 3 weeks.");
});

test("helpers", () => {
  assert.equal(fromISO("2026-02-30"), null);
  assert.equal(toISO(addMonths(new Date(2026, 0, 31), 1)), "2026-02-28", "the month's last day when it's shorter");
  assert.equal(dayDiff(TODAY, new Date(2027, 10, 9)), 365);
  assert.equal(dayDiff(new Date(2026, 2, 7), new Date(2026, 2, 9)), 2, "across a clock change");
  assert.deepEqual([0, 1, -1, 5, -5].map(relative), ["today", "tomorrow", "yesterday", "in 5 days", "5 days ago"]);
});

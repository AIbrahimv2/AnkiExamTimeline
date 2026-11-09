// Dates as the user means them: local calendar days, no times or time zones.
// Stored as yyyy-mm-dd.

const MONTHS = [
  "january", "february", "march", "april", "may", "june",
  "july", "august", "september", "october", "november", "december",
];
const WEEKDAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];

/** A real calendar date, or null (no 31 November). */
export function make(year: number, month: number, day: number): Date | null {
  const d = new Date(year, month, day);
  return d.getFullYear() === year && d.getMonth() === month && d.getDate() === day ? d : null;
}

export function fromISO(iso: string | null | undefined): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  return m ? make(+m[1], +m[2] - 1, +m[3]) : null;
}

export function toISO(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function addDays(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
}

/** The same day n months on, or the month's last day if it's shorter. */
export function addMonths(d: Date, n: number): Date {
  const first = new Date(d.getFullYear(), d.getMonth() + n, 1);
  const last = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
  return new Date(first.getFullYear(), first.getMonth(), Math.min(d.getDate(), last));
}

export function sameDay(a: Date | null, b: Date | null): boolean {
  return !!a && !!b && toISO(a) === toISO(b);
}

/** Calendar days from a to b (positive when b is later). */
export function dayDiff(a: Date, b: Date): number {
  const ua = Date.UTC(a.getFullYear(), a.getMonth(), a.getDate());
  const ub = Date.UTC(b.getFullYear(), b.getMonth(), b.getDate());
  return Math.round((ub - ua) / 86400000);
}

/** "Friday, November 20, 2026" */
export function formatLong(d: Date): string {
  return d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}

/** "Fri, Nov 20, 2026" */
export function formatShort(d: Date): string {
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

/** "November 2026" */
export function formatMonth(year: number, month: number): string {
  return new Date(year, month, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

/** "today", "tomorrow", "in 11 days", "3 days ago" */
export function relative(days: number): string {
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days === -1) return "yesterday";
  return days > 0 ? `in ${days} days` : `${-days} days ago`;
}

function monthIndex(word: string): number {
  const w = word.replace(/\.$/, "");
  if (w.length < 3) return -1;
  return MONTHS.findIndex((m) => m.startsWith(w));
}

function weekdayIndex(word: string): number {
  if (word.length < 2) return -1;
  return WEEKDAYS.findIndex((d) => d.startsWith(word));
}

/** A day and month with no year: this year's, or next year's if it's passed. */
function nextOf(month: number, day: number, today: Date): Date | null {
  const d = make(today.getFullYear(), month, day);
  if (d && dayDiff(today, d) >= 0) return d;
  return make(today.getFullYear() + 1, month, day);
}

function fullYear(y: string): number {
  return y.length === 2 ? 2000 + +y : +y;
}

/**
 * What the user typed, read loosely: "Nov 20", "20 november 2026", "11/20",
 * "2026-11-20", "Fri, Nov 20, 2026", "today", "tomorrow", "in 3 weeks",
 * "+10", "2 months", "next friday", "20th". Null if it isn't a date.
 */
export function parseLoose(text: string, today: Date): Date | null {
  let s = text.trim().toLowerCase().replace(/,/g, " ").replace(/\s+/g, " ");
  if (!s) return null;
  if (s === "today" || s === "now") return today;
  if (["tomorrow", "tmr", "tmrw", "tom"].includes(s)) return addDays(today, 1);
  if (s === "next week") return addDays(today, 7);
  if (s === "next month") return addMonths(today, 1);
  if (s === "next year") return addMonths(today, 12);

  // In so many days, weeks, months or years: "in 3 weeks", "+10", "2 months", "a week".
  const rel = /^(?:in |\+)?(a|an|\d{1,3}) ?(d|days?|w|wks?|weeks?|m|mos?|months?|y|yrs?|years?)?(?: from (?:now|today))?$/.exec(s);
  if (rel && (rel[2] || s.startsWith("in ") || s.startsWith("+"))) {
    const n = rel[1] === "a" || rel[1] === "an" ? 1 : +rel[1];
    const unit = (rel[2] ?? "d")[0];
    if (unit === "d") return addDays(today, n);
    if (unit === "w") return addDays(today, 7 * n);
    if (unit === "m") return addMonths(today, n);
    return addMonths(today, 12 * n);
  }

  // A weekday: the next one after today ("friday", "next fri").
  const wd = /^(?:next |this |on )?([a-z]+)$/.exec(s);
  if (wd && weekdayIndex(wd[1]) >= 0 && monthIndex(wd[1]) < 0) {
    const ahead = (weekdayIndex(wd[1]) - today.getDay() + 7) % 7 || 7;
    return addDays(today, ahead);
  }

  // A leading weekday is just decoration: "fri nov 20 2026".
  s = s.replace(/^([a-z]+) (?=\S)/, (all, word: string) => (weekdayIndex(word) >= 0 && monthIndex(word) < 0 ? "" : all));

  let m = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/.exec(s);
  if (m) return make(+m[1], +m[2] - 1, +m[3]);

  // Month first, as in the US: 11/20, 11/20/26, 11-20-2026.
  m = /^(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2}|\d{4}))?$/.exec(s);
  if (m) return m[3] ? make(fullYear(m[3]), +m[1] - 1, +m[2]) : nextOf(+m[1] - 1, +m[2], today);

  // "nov 20", "november 20th 2026"
  m = /^([a-z]+\.?) (\d{1,2})(?:st|nd|rd|th)?(?: (\d{4}))?$/.exec(s);
  if (m && monthIndex(m[1]) >= 0) {
    return m[3] ? make(+m[3], monthIndex(m[1]), +m[2]) : nextOf(monthIndex(m[1]), +m[2], today);
  }
  // "20 nov", "20th of november 2026"
  m = /^(\d{1,2})(?:st|nd|rd|th)?(?: of)? ([a-z]+\.?)(?: (\d{4}))?$/.exec(s);
  if (m && monthIndex(m[2]) >= 0) {
    return m[3] ? make(+m[3], monthIndex(m[2]), +m[1]) : nextOf(monthIndex(m[2]), +m[1], today);
  }

  // Just a day of the month: the next 20th.
  m = /^(\d{1,2})(?:st|nd|rd|th)?$/.exec(s);
  if (m) {
    for (let i = 0; i < 3; i++) {
      const month = new Date(today.getFullYear(), today.getMonth() + i, 1);
      const d = make(month.getFullYear(), month.getMonth(), +m[1]);
      if (d && dayDiff(today, d) >= 0) return d;
    }
  }
  return null;
}

/**
 * Why a date that didn't parse can't be read, when there's something more
 * useful to say than "can't read it": "November has only 30 days."
 */
export function whyNot(text: string): string | null {
  const s = text.trim().toLowerCase().replace(/,/g, " ").replace(/\s+/g, " ");
  let month = -1;
  let day = 0;
  let m = /(?:^| )([a-z]+\.?) (\d{1,2})(?:st|nd|rd|th)?(?: \d{4})?$/.exec(s);
  if (m) [month, day] = [monthIndex(m[1]), +m[2]];
  m = month < 0 ? /^(\d{1,2})(?:st|nd|rd|th)?(?: of)? ([a-z]+\.?)(?: \d{4})?$/.exec(s) : null;
  if (m) [month, day] = [monthIndex(m[2]), +m[1]];
  m = month < 0 ? /^(\d{1,2})[/.-](\d{1,2})(?:[/.-](?:\d{2}|\d{4}))?$/.exec(s) : null;
  if (m) {
    if (+m[1] > 12 && +m[2] <= 12) return "Put the month first, like 11/20.";
    if (+m[1] < 1 || +m[1] > 12) return "There are only 12 months.";
    [month, day] = [+m[1] - 1, +m[2]];
  }
  if (month < 0) return null;
  const name = MONTHS[month][0].toUpperCase() + MONTHS[month].slice(1);
  if (month === 1 && day === 29) return "February 29 only comes in leap years.";
  const most = new Date(2024, month + 1, 0).getDate();
  return day > most ? `${name} has only ${most} days.` : null;
}

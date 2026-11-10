import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { type KeyboardEvent, type RefObject, useEffect, useRef, useState } from "react";
import { addDays, addMonths, dayDiff, formatLong, formatMonth, relative, sameDay, toISO } from "../dates";

const WEEK = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_NAMES = MONTHS.map((_, m) => new Date(2026, m, 1).toLocaleDateString("en-US", { month: "long" }));

/** Days of a month, the months of a year, or a page of twelve years. */
type Mode = "days" | "months" | "years";

/** The same day of the month in another month and year, or that month's last day. */
function inMonth(d: Date, y: number, m: number): Date {
  return new Date(y, m, Math.min(d.getDate(), new Date(y, m + 1, 0).getDate()));
}

/**
 * A month to pick a day from, drawn by the page: Anki's web view on macOS
 * crashes on the browser's own date picker. Days that already have an exam
 * carry a dot (the name is in the tooltip), so exams that land close together
 * are easy to spot.
 *
 * The title switches to the year's months, and from there to a page of years,
 * to get far quickly; picking one goes back down. Keys: arrows move, Page
 * Up/Down go a month (with Shift, a year), Enter picks, Esc goes back up a
 * level or closes.
 */
export function Calendar(props: {
  value: Date | null;
  today: Date;
  marks: Map<string, string[]>;
  onPick: (d: Date) => void;
  onClose: () => void;
  /** Take the keyboard on opening (otherwise the text box keeps it). */
  takeKeys?: boolean;
  gridRef?: RefObject<HTMLDivElement | null>;
}) {
  const { today, marks } = props;
  const [mode, setMode] = useState<Mode>("days");
  const [cursor, setCursor] = useState<Date>(props.value ?? today);
  const [view, setView] = useState({ y: cursor.getFullYear(), m: cursor.getMonth() });
  const ownGrid = useRef<HTMLDivElement>(null);
  const grid = props.gridRef ?? ownGrid;

  useEffect(() => {
    if (props.takeKeys) grid.current?.focus({ preventScroll: true });
  }, []);

  // Typing a date in the box shows it here.
  const typed = props.value ? toISO(props.value) : null;
  useEffect(() => {
    if (!props.value) return;
    moveTo(props.value);
    setMode("days");
  }, [typed]);

  const moveTo = (d: Date) => {
    setCursor(d);
    setView({ y: d.getFullYear(), m: d.getMonth() });
  };

  // A page of twelve years, starting the year before this one.
  const base = today.getFullYear() - 1;
  const pageStart = base + Math.floor((view.y - base) / 12) * 12;

  /** The arrows beside the title: a month, a year, or a page of years. */
  const shift = (n: number) => {
    if (mode === "days") {
      const first = new Date(view.y, view.m + n, 1);
      setView({ y: first.getFullYear(), m: first.getMonth() });
      setCursor(addMonths(cursor, n));
    } else {
      const years = mode === "months" ? n : 12 * n;
      setView({ y: view.y + years, m: view.m });
      setCursor(addMonths(cursor, 12 * years));
    }
  };

  const pickMonth = (y: number, m: number) => {
    moveTo(inMonth(cursor, y, m));
    setMode("days");
  };
  const pickYear = (y: number) => {
    moveTo(inMonth(cursor, y, cursor.getMonth()));
    setMode("months");
  };

  const onKey = (e: KeyboardEvent) => {
    // Months and years are three to a row.
    const unit = mode === "days" ? null : mode === "months" ? 1 : 12;
    const step: Record<string, () => Date> = unit
      ? {
          ArrowLeft: () => addMonths(cursor, -unit),
          ArrowRight: () => addMonths(cursor, unit),
          ArrowUp: () => addMonths(cursor, -3 * unit),
          ArrowDown: () => addMonths(cursor, 3 * unit),
          PageUp: () => addMonths(cursor, -12 * (mode === "months" ? 1 : 12)),
          PageDown: () => addMonths(cursor, 12 * (mode === "months" ? 1 : 12)),
        }
      : {
          ArrowLeft: () => addDays(cursor, -1),
          ArrowRight: () => addDays(cursor, 1),
          ArrowUp: () => addDays(cursor, -7),
          ArrowDown: () => addDays(cursor, 7),
          PageUp: () => addMonths(cursor, e.shiftKey ? -12 : -1),
          PageDown: () => addMonths(cursor, e.shiftKey ? 12 : 1),
          Home: () => addDays(cursor, -cursor.getDay()),
          End: () => addDays(cursor, 6 - cursor.getDay()),
        };
    if (step[e.key]) {
      e.preventDefault();
      moveTo(step[e.key]());
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (mode === "days") props.onPick(cursor);
      else if (mode === "months") pickMonth(cursor.getFullYear(), cursor.getMonth());
      else pickYear(cursor.getFullYear());
    } else if (e.key === "Escape") {
      // Not on to Anki's own Esc listener, which would close the window.
      e.preventDefault();
      e.stopPropagation();
      if (mode === "years") setMode("months");
      else if (mode === "months") setMode("days");
      else props.onClose();
    }
  };

  const label = { days: "month", months: "year", years: "" }[mode];
  const title =
    mode === "days" ? formatMonth(view.y, view.m) : mode === "months" ? String(view.y) : `${pageStart} – ${pageStart + 11}`;
  const unitName = { days: "month", months: "year", years: "twelve years" }[mode];
  const now = { y: today.getFullYear(), m: today.getMonth() };
  const value = props.value;
  const hasExam = (prefix: string) => [...marks.keys()].some((iso) => iso.startsWith(prefix));
  const pad = (m: number) => String(m + 1).padStart(2, "0");

  return (
    // Clicks in the calendar never move focus, so you can keep typing in the
    // box; tabIndex keeps any stray focus inside the field all the same.
    <div className="cal" role="dialog" aria-label="Choose a date" tabIndex={-1} onMouseDown={(e) => e.preventDefault()}>
      <div className="cal-head">
        <button
          type="button"
          className="icon-btn"
          aria-label={`Previous ${unitName}`}
          title={`Previous ${unitName}${mode === "days" ? " (Page Up)" : ""}`}
          onClick={() => shift(-1)}
        >
          <ChevronLeft size={16} />
        </button>
        {label ? (
          <button
            type="button"
            className="cal-title"
            aria-label={`${title}: choose a ${label}`}
            title={`Choose a ${label}`}
            onClick={() => setMode(mode === "days" ? "months" : "years")}
          >
            {title}
            <ChevronDown size={14} strokeWidth={2.4} />
          </button>
        ) : (
          <div className="cal-title">{title}</div>
        )}
        <button
          type="button"
          className="icon-btn"
          aria-label={`Next ${unitName}`}
          title={`Next ${unitName}${mode === "days" ? " (Page Down)" : ""}`}
          onClick={() => shift(1)}
        >
          <ChevronRight size={16} />
        </button>
      </div>
      <div className={`cal-grid ${mode}`} ref={grid} tabIndex={0} role="grid" onKeyDown={onKey}>
        {mode === "days" && (
          <>
            {WEEK.map((w) => (
              <div key={w} className="cal-dow" role="columnheader">
                {w}
              </div>
            ))}
            {days(view).map((d) => {
              const iso = toISO(d);
              const names = marks.get(iso);
              const diff = dayDiff(today, d);
              const cls = [
                "cal-day",
                d.getMonth() !== view.m && "out",
                diff < 0 && "past",
                diff === 0 && "today",
                sameDay(d, value) && "picked",
                sameDay(d, cursor) && "cursor",
              ];
              const tip = [formatLong(d), relative(diff), ...(names ?? [])].join("\n");
              return (
                <button
                  type="button"
                  key={iso}
                  className={cls.filter(Boolean).join(" ")}
                  tabIndex={-1}
                  title={tip}
                  aria-label={tip.replace(/\n/g, ", ")}
                  aria-selected={sameDay(d, value)}
                  onClick={() => props.onPick(d)}
                >
                  {d.getDate()}
                  {names && <span className="cal-dot" aria-hidden="true" />}
                </button>
              );
            })}
          </>
        )}
        {mode === "months" &&
          MONTHS.map((name, m) => {
            const y = view.y;
            const cls = [
              "cal-day",
              y * 12 + m < now.y * 12 + now.m && "past",
              y === now.y && m === now.m && "today",
              value && value.getFullYear() === y && value.getMonth() === m && "picked",
              cursor.getFullYear() === y && cursor.getMonth() === m && "cursor",
            ];
            return (
              <button
                type="button"
                key={name}
                className={cls.filter(Boolean).join(" ")}
                tabIndex={-1}
                aria-label={`${MONTH_NAMES[m]} ${y}`}
                onClick={() => pickMonth(y, m)}
              >
                {name}
                {hasExam(`${y}-${pad(m)}`) && <span className="cal-dot" aria-hidden="true" />}
              </button>
            );
          })}
        {mode === "years" &&
          Array.from({ length: 12 }, (_, i) => pageStart + i).map((y) => {
            const cls = [
              "cal-day",
              y < now.y && "past",
              y === now.y && "today",
              value?.getFullYear() === y && "picked",
              cursor.getFullYear() === y && "cursor",
            ];
            return (
              <button
                type="button"
                key={y}
                className={cls.filter(Boolean).join(" ")}
                tabIndex={-1}
                aria-label={String(y)}
                onClick={() => pickYear(y)}
              >
                {y}
                {hasExam(`${y}-`) && <span className="cal-dot" aria-hidden="true" />}
              </button>
            );
          })}
      </div>
    </div>
  );
}

/** Six weeks from the Sunday on or before the month's first day. */
function days(view: { y: number; m: number }): Date[] {
  const first = new Date(view.y, view.m, 1);
  const start = addDays(first, -first.getDay());
  return Array.from({ length: 42 }, (_, i) => addDays(start, i));
}

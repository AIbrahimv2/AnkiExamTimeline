import { ChevronLeft, ChevronRight } from "lucide-react";
import { type KeyboardEvent, type RefObject, useEffect, useRef, useState } from "react";
import { addDays, addMonths, dayDiff, formatLong, formatMonth, relative, sameDay, toISO } from "../dates";

const WEEK = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

/** Quick picks under the month: a few common distances from today. */
const QUICK: { label: string; at: (today: Date) => Date }[] = [
  { label: "1 week", at: (t) => addDays(t, 7) },
  { label: "2 weeks", at: (t) => addDays(t, 14) },
  { label: "1 month", at: (t) => addMonths(t, 1) },
  { label: "3 months", at: (t) => addMonths(t, 3) },
];

/**
 * A month to pick a day from, drawn by the page: Anki's web view on macOS
 * crashes on the browser's own date picker. Days that already have an exam
 * carry a dot (the name is in the tooltip), so exams that land close together
 * are easy to spot. Arrow keys move a day or a week, Page Up/Down a month
 * (with Shift, a year), Enter picks, Esc closes.
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
    if (props.value) moveTo(props.value);
  }, [typed]);

  const moveTo = (d: Date) => {
    setCursor(d);
    setView({ y: d.getFullYear(), m: d.getMonth() });
  };
  const shiftMonth = (n: number) => {
    const first = new Date(view.y, view.m + n, 1);
    setView({ y: first.getFullYear(), m: first.getMonth() });
    setCursor(addMonths(cursor, n));
  };

  const onKey = (e: KeyboardEvent) => {
    const step: Record<string, () => Date> = {
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
      props.onPick(cursor);
    } else if (e.key === "Escape") {
      // Not on to Anki's own Esc listener, which would close the window.
      e.preventDefault();
      e.stopPropagation();
      props.onClose();
    }
  };

  const first = new Date(view.y, view.m, 1);
  const start = addDays(first, -first.getDay());
  const days = Array.from({ length: 42 }, (_, i) => addDays(start, i));

  return (
    // tabIndex: a click on the calendar's background keeps focus inside the
    // field, so it doesn't count as leaving it.
    <div className="cal" role="dialog" aria-label="Choose a date" tabIndex={-1}>
      <div className="cal-head">
        <button type="button" className="icon-btn" aria-label="Previous month" title="Previous month (Page Up)" onClick={() => shiftMonth(-1)}>
          <ChevronLeft size={16} />
        </button>
        <div className="cal-title">{formatMonth(view.y, view.m)}</div>
        <button type="button" className="icon-btn" aria-label="Next month" title="Next month (Page Down)" onClick={() => shiftMonth(1)}>
          <ChevronRight size={16} />
        </button>
      </div>
      <div className="cal-grid" ref={grid} tabIndex={0} role="grid" onKeyDown={onKey}>
        {WEEK.map((w) => (
          <div key={w} className="cal-dow" role="columnheader">
            {w}
          </div>
        ))}
        {days.map((d) => {
          const iso = toISO(d);
          const names = marks.get(iso);
          const diff = dayDiff(today, d);
          const cls = [
            "cal-day",
            d.getMonth() !== view.m && "out",
            diff < 0 && "past",
            diff === 0 && "today",
            sameDay(d, props.value) && "picked",
            sameDay(d, cursor) && "cursor",
          ]
            .filter(Boolean)
            .join(" ");
          const tip = [formatLong(d), relative(diff), ...(names ?? [])].join("\n");
          return (
            <button
              type="button"
              key={iso}
              className={cls}
              tabIndex={-1}
              title={tip}
              aria-label={tip.replace(/\n/g, ", ")}
              aria-selected={sameDay(d, props.value)}
              onClick={() => props.onPick(d)}
            >
              {d.getDate()}
              {names && <span className="cal-dot" aria-hidden="true" />}
            </button>
          );
        })}
      </div>
      <div className="cal-quick">
        {QUICK.map((q) => (
          <button
            type="button"
            key={q.label}
            className="chip"
            title={`In ${q.label}: ${formatLong(q.at(today))}`}
            aria-label={`In ${q.label}, ${formatLong(q.at(today))}`}
            onClick={() => props.onPick(q.at(today))}
          >
            {q.label}
          </button>
        ))}
      </div>
    </div>
  );
}

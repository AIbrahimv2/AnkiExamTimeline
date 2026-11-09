import { CalendarDays } from "lucide-react";
import { type KeyboardEvent, type RefObject, useEffect, useId, useMemo, useRef, useState } from "react";
import { dayDiff, formatLong, formatShort, fromISO, parseLoose, relative, toISO, whyNot } from "../dates";
import { Calendar } from "./Calendar";

/**
 * A date you can type the way you'd say it ("Nov 20", "in 3 weeks", "next
 * friday") or pick from the calendar, which opens while the box has focus and
 * shows the date as it's typed. How far away it is sits at the end of the box
 * (the full date in its tooltip); a date it can't read is explained below.
 */
export function DateField(props: {
  value: string | null;
  onChange: (iso: string | null) => void;
  today: string;
  marks: Map<string, string[]>;
  /** Show the hint as an error (the form was submitted without a date). */
  showError?: boolean;
  /** Enter in the text box (it closes the calendar too). */
  onEnter?: () => void;
  placeholder?: string;
  inputRef?: RefObject<HTMLInputElement | null>;
  label: string;
}) {
  const today = useMemo(() => fromISO(props.today) ?? new Date(), [props.today]);
  const value = fromISO(props.value);
  const [text, setText] = useState(value ? formatShort(value) : "");
  const [open, setOpen] = useState(false);
  // Whether the calendar takes the keys when it opens (the icon, or ↓) or
  // leaves them in the text box (it opens whenever the box has focus, so you
  // can type or pick).
  const [grab, setGrab] = useState(false);
  const grid = useRef<HTMLDivElement>(null);
  // Set while the field puts focus back in the box itself (after a pick, or
  // Esc), so that doesn't open the calendar again.
  const quiet = useRef(false);
  const noteId = useId();
  // The value this field last sent up, so its own echo doesn't rewrite the text.
  const sent = useRef<string | null>(props.value);
  const box = useRef<HTMLDivElement>(null);
  const ownInput = useRef<HTMLInputElement>(null);
  const input = props.inputRef ?? ownInput;

  // A new value from outside (cleared after adding, say) shows as the tidy
  // short date. What the user is typing is left alone.
  useEffect(() => {
    if (props.value === sent.current) return;
    sent.current = props.value;
    setText(value ? formatShort(value) : "");
  }, [props.value]);

  const send = (iso: string | null) => {
    sent.current = iso;
    props.onChange(iso);
  };

  const show = (takeKeys: boolean) => {
    setGrab(takeKeys);
    setOpen(true);
    if (takeKeys && open) grid.current?.focus();
  };

  // Clicking anywhere else closes the calendar.
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => box.current && !box.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);

  const parsed = text.trim() ? parseLoose(text, today) : null;

  const type = (t: string) => {
    setText(t);
    const d = t.trim() ? parseLoose(t, today) : null;
    send(d ? toISO(d) : null);
  };

  const refocus = () => {
    quiet.current = true;
    input.current?.focus();
    quiet.current = false;
  };

  const pick = (d: Date) => {
    setText(formatShort(d));
    send(toISO(d));
    setOpen(false);
    refocus();
  };

  const onKey = (e: KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      show(true);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (parsed) setText(formatShort(parsed));
      setOpen(false);
      props.onEnter?.();
    } else if (e.key === "Escape" && open) {
      e.preventDefault();
      e.stopPropagation();
      setOpen(false);
    }
  };

  const bad = !!text.trim() && !parsed;
  const missing = !text.trim() && props.showError;
  return (
    <div
      className="datefield"
      ref={box}
      onBlur={(e) => {
        // Focus left the field and its calendar (Tab, or a click elsewhere).
        if (!box.current?.contains(e.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      <div className={`df-box${bad || missing ? " bad" : ""}${open ? " open" : ""}`}>
        <button
          type="button"
          className="df-cal"
          aria-label="Open the calendar"
          aria-expanded={open}
          title="Open the calendar (↓)"
          tabIndex={-1} /* Tab goes straight to the box, which opens it anyway */
          onMouseDown={(e) => e.preventDefault() /* focus stays put; the click decides */}
          onClick={() => (open ? setOpen(false) : show(true))}
        >
          <CalendarDays size={16} />
        </button>
        <input
          ref={input}
          type="text"
          aria-label={props.label}
          placeholder={props.placeholder ?? "Exam date"}
          aria-describedby={parsed || bad || missing ? noteId : undefined}
          value={text}
          spellCheck={false}
          autoComplete="off"
          onFocus={() => !quiet.current && show(false)}
          onClick={() => show(false)}
          onBlur={() => parsed && setText(formatShort(parsed))}
          onChange={(e) => type(e.target.value)}
          onKeyDown={onKey}
        />
        {parsed && (
          <span
            id={noteId}
            className={`df-rel${dayDiff(today, parsed) < 0 ? " past" : ""}`}
            title={formatLong(parsed)}
            aria-label={`${formatLong(parsed)}, ${relative(dayDiff(today, parsed))}`}
          >
            {relative(dayDiff(today, parsed))}
          </span>
        )}
      </div>
      {(bad || missing) && (
        <div id={noteId} className="df-hint" aria-live="polite">
          {bad ? whyNot(text) ?? "Can't read that date. Try “Nov 20” or “in 3 weeks”." : "Pick a date for the exam."}
        </div>
      )}
      {open && (
        <Calendar
          value={parsed ?? value}
          today={today}
          marks={props.marks}
          gridRef={grid}
          takeKeys={grab}
          onPick={pick}
          onClose={() => {
            setOpen(false);
            refocus();
          }}
        />
      )}
    </div>
  );
}

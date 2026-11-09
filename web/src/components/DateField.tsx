import { CalendarDays } from "lucide-react";
import { type KeyboardEvent, type RefObject, useEffect, useMemo, useRef, useState } from "react";
import { dayDiff, formatLong, formatShort, fromISO, parseLoose, relative, toISO, whyNot } from "../dates";
import { Calendar } from "./Calendar";

/**
 * A date you can type the way you'd say it ("Nov 20", "in 3 weeks", "next
 * friday") or pick from a calendar. Underneath, it spells out the date it
 * understood and how far away it is, so a typo can't slip through.
 */
export function DateField(props: {
  value: string | null;
  onChange: (iso: string | null) => void;
  today: string;
  marks: Map<string, string[]>;
  /** Show the hint as an error (the form was submitted without a date). */
  showError?: boolean;
  /** Enter in the text box, with the calendar closed. */
  onEnter?: () => void;
  placeholder?: string;
  inputRef?: RefObject<HTMLInputElement | null>;
  label: string;
}) {
  const today = useMemo(() => fromISO(props.today) ?? new Date(), [props.today]);
  const value = fromISO(props.value);
  const [text, setText] = useState(value ? formatShort(value) : "");
  const [open, setOpen] = useState(false);
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

  const pick = (d: Date) => {
    setText(formatShort(d));
    send(toISO(d));
    setOpen(false);
    input.current?.focus();
  };

  const onKey = (e: KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
    } else if (e.key === "Enter" && !open) {
      e.preventDefault();
      if (parsed) setText(formatShort(parsed));
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
    <div className="datefield" ref={box}>
      <div className={`df-box${bad || missing ? " bad" : ""}${open ? " open" : ""}`}>
        <button
          type="button"
          className="df-cal"
          aria-label="Open the calendar"
          aria-expanded={open}
          title="Open the calendar (↓)"
          onClick={() => setOpen((o) => !o)}
        >
          <CalendarDays size={16} />
        </button>
        <input
          ref={input}
          type="text"
          aria-label={props.label}
          placeholder={props.placeholder ?? "Date, like Nov 20 or in 3 weeks"}
          value={text}
          spellCheck={false}
          autoComplete="off"
          onBlur={() => parsed && setText(formatShort(parsed))}
          onChange={(e) => type(e.target.value)}
          onKeyDown={onKey}
        />
      </div>
      <div className={`df-hint${bad || missing ? " bad" : ""}`} aria-live="polite">
        {parsed ? (
          <>
            <span className="df-long">{formatLong(parsed)}</span>
            <span className={`df-rel${dayDiff(today, parsed) < 0 ? " past" : ""}`}>{relative(dayDiff(today, parsed))}</span>
          </>
        ) : bad ? (
          whyNot(text) ?? "Can't read that date. Try “Nov 20”, “11/20” or “in 3 weeks”."
        ) : missing ? (
          "Pick a date for the exam."
        ) : (
          "Type it, or pick it from the calendar."
        )}
      </div>
      {open && <Calendar value={parsed ?? value} today={today} marks={props.marks} onPick={pick} onClose={() => { setOpen(false); input.current?.focus(); }} />}
    </div>
  );
}

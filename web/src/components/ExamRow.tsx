import { Check, Pencil, X } from "lucide-react";
import { useRef, useState } from "react";
import { dayDiff, formatLong, fromISO } from "../dates";
import type { Exam } from "../types";
import { DateField } from "./DateField";
import { NameField } from "./NameField";

/** The big number on the left and what it counts. */
function countdown(days: number): { big: string; unit: string } {
  if (days === 0) return { big: "0", unit: "today" };
  if (days > 0) return { big: String(days), unit: days === 1 ? "day left" : "days left" };
  return { big: String(-days), unit: days === -1 ? "day ago" : "days ago" };
}

export function ExamRow(props: {
  exam: Exam;
  today: string;
  marks: Map<string, string[]>;
  onSave: (exam: Exam, name: string, date: string) => Promise<boolean>;
  onRemove: (exam: Exam) => void;
}) {
  const { exam } = props;
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(exam.name);
  const [date, setDate] = useState<string | null>(exam.date);
  const [tried, setTried] = useState(false);
  const nameInput = useRef<HTMLInputElement>(null);

  const when = fromISO(exam.date);
  const days = when ? dayDiff(fromISO(props.today) ?? new Date(), when) : 0;
  const { big, unit } = countdown(days);

  const start = () => {
    setName(exam.name);
    setDate(exam.date);
    setTried(false);
    setEditing(true);
    requestAnimationFrame(() => nameInput.current?.select());
  };
  const save = async () => {
    setTried(true);
    if (!name.trim() || !date) return;
    if (await props.onSave(exam, name, date)) setEditing(false);
  };

  if (editing) {
    // Other exams' days stay marked in the calendar; this one's own doesn't.
    const marks = new Map(props.marks);
    const left = (marks.get(exam.date) ?? []).filter((n) => n !== exam.name);
    if (left.length) marks.set(exam.date, left);
    else marks.delete(exam.date);
    return (
      <div
        className="exam editing"
        onKeyDown={(e) => {
          // Stop it here: Anki's own Esc listener on the page closes the window.
          if (e.key === "Escape" && !e.defaultPrevented) {
            e.preventDefault();
            e.stopPropagation();
            setEditing(false);
          }
        }}
      >
        <NameField value={name} onChange={setName} onEnter={save} showError={tried} inputRef={nameInput} />
        <DateField value={date} onChange={setDate} today={props.today} marks={marks} showError={tried} onEnter={save} label="Exam date" />
        <div className="edit-actions">
          <button type="button" className="btn ghost" onClick={() => setEditing(false)}>
            Cancel
          </button>
          <button type="button" className="btn primary" onClick={save}>
            <Check size={14} strokeWidth={2.6} /> Save
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`exam${days < 0 ? " past" : ""}${days === 0 ? " is-today" : ""}`}>
      <div className="exam-count" aria-label={`${big} ${unit}`}>
        <span className="exam-big">{big}</span>
        <span className="exam-unit">{unit}</span>
      </div>
      <div className="exam-main">
        <div className="exam-name">{exam.name}</div>
        <div className="exam-date">{when ? formatLong(when) : exam.date}</div>
      </div>
      <div className="exam-actions">
        <button type="button" className="icon-btn" aria-label={`Edit ${exam.name}`} title="Edit" onClick={start}>
          <Pencil size={15} />
        </button>
        <button type="button" className="icon-btn bad" aria-label={`Remove ${exam.name}`} title="Remove" onClick={() => props.onRemove(exam)}>
          <X size={16} />
        </button>
      </div>
    </div>
  );
}

import { ChevronRight, Plus } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { call } from "./bridge";
import { DateField } from "./components/DateField";
import { ExamRow } from "./components/ExamRow";
import { dayDiff, fromISO } from "./dates";
import type { Exam, State } from "./types";

interface Toast {
  id: number;
  text: string;
  undo?: Exam;
}

export function App() {
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const [showPast, setShowPast] = useState(false);

  const [name, setName] = useState("");
  const [date, setDate] = useState<string | null>(null);
  const [tried, setTried] = useState(false);
  const nameInput = useRef<HTMLInputElement>(null);

  const load = useCallback(() => call<State>("load").then(setState, (e: Error) => setError(e.message)), []);
  useEffect(() => {
    load();
    // Python asks for a reload when the window is reopened.
    window.examTimeline = { reload: load };
    nameInput.current?.focus();
  }, [load]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast((cur) => (cur?.id === toast.id ? null : cur)), 6000);
    return () => clearTimeout(t);
  }, [toast]);

  const say = (text: string, undo?: Exam) => setToast({ id: Date.now(), text, undo });
  const run = async (cmd: string, args: Record<string, unknown>) => {
    try {
      const next = await call<State>(cmd, args);
      setState(next);
      setError(null);
      return next;
    } catch (e) {
      setError((e as Error).message);
      return null;
    }
  };

  const add = async () => {
    setTried(true);
    if (!name.trim()) return nameInput.current?.focus();
    if (!date) return;
    const next = await run("add", { name, date });
    if (!next) return;
    say(`Added ${name.trim()}`);
    setName("");
    setDate(null);
    setTried(false);
    nameInput.current?.focus();
  };

  const today = fromISO(state?.today) ?? new Date();
  const { upcoming, past, marks } = useMemo(() => {
    const exams = state?.exams ?? [];
    const withDays = exams.map((e) => ({ e, days: dayDiff(today, fromISO(e.date) ?? today) }));
    const marks = new Map<string, string[]>();
    for (const e of exams) marks.set(e.date, [...(marks.get(e.date) ?? []), e.name]);
    return {
      upcoming: withDays.filter((x) => x.days >= 0).sort((a, b) => a.days - b.days).map((x) => x.e),
      past: withDays.filter((x) => x.days < 0).sort((a, b) => b.days - a.days).map((x) => x.e),
      marks,
    };
  }, [state]);

  if (!state) return <div className="loading">{error ?? "Loading…"}</div>;

  const row = (e: Exam) => (
    <ExamRow
      key={e.id}
      exam={e}
      today={state.today}
      marks={marks}
      onSave={async (exam, n, d) => !!(await run("update", { id: exam.id, name: n, date: d }))}
      onRemove={async (exam) => {
        if (await run("remove", { id: exam.id })) say(`Removed ${exam.name}`, exam);
      }}
    />
  );

  return (
    <div className="page">
      <section className="card add">
        <h2>Add an exam</h2>
        <input
          ref={nameInput}
          className={`text${tried && !name.trim() ? " bad" : ""}`}
          aria-label="Exam name"
          placeholder="Exam name, like USMLE Step 1"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
        />
        <div className="add-row">
          <DateField value={date} onChange={setDate} today={state.today} marks={marks} showError={tried} onEnter={add} label="Exam date" />
          <button type="button" className="btn primary add-btn" onClick={add}>
            <Plus size={15} strokeWidth={2.6} /> Add exam
          </button>
        </div>
        {tried && !name.trim() && <div className="form-error">Give the exam a name.</div>}
      </section>

      {error && <div className="banner-error">{error}</div>}

      <section className="list">
        <h2>
          Upcoming <span className="count">{upcoming.length}</span>
        </h2>
        {upcoming.length ? (
          upcoming.map(row)
        ) : (
          <div className="empty">No upcoming exams. Add one above and it shows on the deck screen.</div>
        )}
      </section>

      {past.length > 0 && (
        <section className="list past-list">
          <button type="button" className="past-toggle" aria-expanded={showPast} onClick={() => setShowPast((s) => !s)}>
            <ChevronRight size={15} className={showPast ? "open" : ""} />
            Past <span className="count">{past.length}</span>
          </button>
          {showPast && past.map(row)}
        </section>
      )}

      {toast && (
        <div className="toast" role="status">
          <span>{toast.text}</span>
          {toast.undo && (
            <button
              type="button"
              className="btn ghost sm"
              onClick={async () => {
                const exam = toast.undo;
                setToast(null);
                if (exam && (await run("restore", { exam }))) say(`Put back ${exam.name}`);
              }}
            >
              Undo
            </button>
          )}
        </div>
      )}
    </div>
  );
}

import { ChevronRight, Plus } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { call } from "./bridge";
import { ConfirmRemove } from "./components/ConfirmRemove";
import { DateField } from "./components/DateField";
import { ExamRow } from "./components/ExamRow";
import { NameField } from "./components/NameField";
import { Toast, type ToastMessage } from "./components/Toast";
import { dayDiff, formatLong, fromISO, relative } from "./dates";
import type { Exam, State } from "./types";

export function App() {
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  // The exam just added, saved or put back: lit up in the list for a moment.
  const [flash, setFlash] = useState<Exam["id"] | null>(null);
  const [showPast, setShowPast] = useState(false);
  // The exam waiting on "Remove it?", and what had focus before asking.
  const [confirming, setConfirming] = useState<{ exam: Exam; from: Element | null } | null>(null);

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
    if (flash === null) return;
    const t = setTimeout(() => setFlash(null), 1800);
    return () => clearTimeout(t);
  }, [flash]);

  const say = (msg: Omit<ToastMessage, "id">) => setToast({ ...msg, id: Date.now() });
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
    const exam = next.exams.find((e) => e.id === next.added);
    if (exam) {
      spotlight(exam);
      say({
        kind: "added",
        title: `Added ${exam.name}`,
        detail: describe(exam),
        undo: async () => {
          if (await run("remove", { id: exam.id })) undone(`${exam.name} is off the list again.`);
        },
      });
    }
    setName("");
    setDate(null);
    setTried(false);
    nameInput.current?.focus();
  };

  const today = fromISO(state?.today) ?? new Date();

  const daysTo = (exam: Exam) => dayDiff(today, fromISO(exam.date) ?? today);

  /** Show an exam in the list: open Past if that's where it is, and light it up. */
  const spotlight = (exam: Exam) => {
    if (daysTo(exam) < 0) setShowPast(true);
    setFlash(exam.id);
  };

  /** Its date and how far away, or where it went if the date has passed. */
  const describe = (exam: Exam) => {
    const when = fromISO(exam.date);
    if (!when) return exam.date;
    const days = daysTo(exam);
    if (days < 0) return "The date has passed, so it's under Past.";
    return (
      <>
        <span>{formatLong(when)}</span>
        <span className="toast-rel">{relative(days)}</span>
      </>
    );
  };

  const undone = (detail: string) => say({ kind: "undone", title: "Undone", detail });
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
      flash={flash === e.id}
      onSave={async (exam, n, d) => {
        const next = await run("update", { id: exam.id, name: n, date: d });
        const saved = next?.exams.find((x) => x.id === exam.id);
        if (!saved) return false;
        spotlight(saved);
        say({
          kind: "saved",
          title: `Saved ${saved.name}`,
          detail: describe(saved),
          undo: async () => {
            if (await run("update", { id: exam.id, name: exam.name, date: exam.date })) {
              spotlight(exam);
              undone(`${exam.name} is as it was.`);
            }
          },
        });
        return true;
      }}
      onRemove={(exam) => setConfirming({ exam, from: document.activeElement })}
    />
  );

  return (
    <div className="page">
      <section className="card add">
        <h2>Add an exam</h2>
        <NameField value={name} onChange={setName} onEnter={add} showError={tried} inputRef={nameInput} />
        <div className="add-row">
          <DateField value={date} onChange={setDate} today={state.today} marks={marks} showError={tried} onEnter={add} label="Exam date" />
          <button type="button" className="btn primary add-btn" onClick={add}>
            <Plus size={15} strokeWidth={2.6} /> Add exam
          </button>
        </div>
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

      {confirming && (
        <ConfirmRemove
          exam={confirming.exam}
          onCancel={() => {
            setConfirming(null);
            (confirming.from as HTMLElement | null)?.focus?.();
          }}
          onConfirm={async () => {
            const { exam } = confirming;
            setConfirming(null);
            nameInput.current?.focus();
            if (!(await run("remove", { id: exam.id }))) return;
            say({
              kind: "removed",
              title: `Removed ${exam.name}`,
              detail: fromISO(exam.date) ? formatLong(fromISO(exam.date)!) : exam.date,
              undo: async () => {
                if (await run("restore", { exam })) {
                  spotlight(exam);
                  undone(`${exam.name} is back.`);
                }
              },
            });
          }}
        />
      )}

      {toast && <Toast key={toast.id} toast={toast} onClose={() => setToast((cur) => (cur?.id === toast.id ? null : cur))} />}
    </div>
  );
}

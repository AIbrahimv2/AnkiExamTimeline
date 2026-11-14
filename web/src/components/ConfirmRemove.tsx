import { type KeyboardEvent, useEffect, useRef } from "react";
import { formatLong, fromISO } from "../dates";
import type { Exam } from "../types";

/**
 * "Remove this exam?", drawn by the page rather than with confirm(): native
 * popups from Anki's web view are best avoided on macOS. Enter removes, Esc
 * or a click outside keeps it, and Tab stays between the two buttons.
 */
export function ConfirmRemove(props: { exam: Exam; onConfirm: () => void; onCancel: () => void }) {
  const remove = useRef<HTMLButtonElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  useEffect(() => remove.current?.focus(), []);

  const when = fromISO(props.exam.date);

  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      // Not on to Anki's own Esc listener, which would close the window.
      e.preventDefault();
      e.stopPropagation();
      props.onCancel();
    } else if (e.key === "Tab") {
      e.preventDefault();
      (document.activeElement === remove.current ? cancel : remove).current?.focus();
    }
  };

  return (
    <div
      className="overlay"
      onMouseDown={(e) => e.target === e.currentTarget && props.onCancel()}
      onKeyDown={onKey}
    >
      <div className="modal confirm" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-body">
        <h3 id="confirm-title">Remove {props.exam.name}?</h3>
        <p id="confirm-body">{when ? formatLong(when) : props.exam.date}</p>
        <div className="modal-actions">
          <button ref={cancel} type="button" className="btn" onClick={props.onCancel}>
            Cancel
          </button>
          <button ref={remove} type="button" className="btn danger" onClick={props.onConfirm}>
            Remove
          </button>
        </div>
      </div>
    </div>
  );
}

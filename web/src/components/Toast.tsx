import { CalendarPlus, Check, Trash2, Undo2, X } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";

export interface ToastMessage {
  id: number;
  kind: "added" | "saved" | "removed" | "undone";
  title: string;
  detail?: ReactNode;
  /** Shown as an Undo button. */
  undo?: () => void;
}

const ICONS = { added: CalendarPlus, saved: Check, removed: Trash2, undone: Undo2 };
const SHOWN_FOR = 5000;

/**
 * What just changed, at the bottom of the window: an icon for the kind of
 * change, the exam and its date, and Undo. It stays while the pointer is on
 * it, and fades out after a few seconds otherwise. Remount it (key it by id)
 * for each new message.
 */
export function Toast(props: { toast: ToastMessage; onClose: () => void }) {
  const { toast } = props;
  const [hover, setHover] = useState(false);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    if (hover || leaving) return;
    const t = setTimeout(() => setLeaving(true), SHOWN_FOR);
    return () => clearTimeout(t);
  }, [hover, leaving]);

  useEffect(() => {
    if (!leaving) return;
    const t = setTimeout(props.onClose, 160);
    return () => clearTimeout(t);
  }, [leaving]);

  const Icon = ICONS[toast.kind];
  return (
    <div
      className={`toast ${toast.kind}${leaving ? " leaving" : ""}`}
      role="status"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <span className="toast-icon" aria-hidden="true">
        <Icon size={15} strokeWidth={2.2} />
      </span>
      <div className="toast-text">
        <div className="toast-title">{toast.title}</div>
        {toast.detail && <div className="toast-detail">{toast.detail}</div>}
      </div>
      {toast.undo && (
        <button type="button" className="btn sm toast-undo" onClick={toast.undo}>
          <Undo2 size={13} strokeWidth={2.4} /> Undo
        </button>
      )}
      <button type="button" className="icon-btn toast-close" aria-label="Dismiss" title="Dismiss" onClick={() => setLeaving(true)}>
        <X size={14} />
      </button>
    </div>
  );
}

import { Ellipsis, Info, Sparkles } from "lucide-react";
import { useRef, useState } from "react";
import { type Anchor, anchorBelow, Menu } from "../kit/controls";
import type { KitTab } from "../kit/types";

/** The ⋯ menu: What's new and About, in the dialog every one of the
 *  add-ons shares. A dot says there's an update you haven't read about. */
export function MoreMenu(props: { unseen: boolean; onPick: (tab: KitTab) => void }) {
  const btn = useRef<HTMLButtonElement>(null);
  const [anchor, setAnchor] = useState<Anchor | null>(null);
  return (
    <>
      <button
        ref={btn}
        type="button"
        className="icon-btn"
        title="More"
        aria-label="More"
        onClick={() => btn.current && setAnchor(anchorBelow(btn.current, true))}
      >
        <Ellipsis size={17} />
        {props.unseen && <span className="kit-dot" aria-label="What's new" />}
      </button>
      {anchor && (
        <Menu
          anchor={anchor}
          minWidth={220}
          onClose={() => setAnchor(null)}
          entries={[
            { label: "What's new", icon: <Sparkles size={14} />, dot: props.unseen, onSelect: () => props.onPick("news") },
            { label: "About Exam Timeline", icon: <Info size={14} />, onSelect: () => props.onPick("about") },
          ]}
        />
      )}
    </>
  );
}

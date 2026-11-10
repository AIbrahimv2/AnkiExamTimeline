import { type RefObject, useId } from "react";

/** The exam's name, with "Give the exam a name." under it when it's left empty. */
export function NameField(props: {
  value: string;
  onChange: (name: string) => void;
  onEnter: () => void;
  /** The form was submitted: an empty name is now an error. */
  showError: boolean;
  inputRef?: RefObject<HTMLInputElement | null>;
}) {
  const id = useId();
  const bad = props.showError && !props.value.trim();
  return (
    <div className="field">
      <input
        ref={props.inputRef}
        className={`text${bad ? " bad" : ""}`}
        aria-label="Exam name"
        aria-invalid={bad}
        aria-describedby={bad ? id : undefined}
        placeholder="Exam name"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && props.onEnter()}
      />
      {bad && (
        <div id={id} className="field-error name-error">
          Give the exam a name.
        </div>
      )}
    </div>
  );
}

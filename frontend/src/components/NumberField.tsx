import { useEffect, useState } from "react";

export type FieldKind = "pct" | "millions" | "raw";

interface Props {
  label: string;
  anchor?: string;
  value: number | null;
  onChange: (value: number | null) => void;
  kind: FieldKind;
  missing?: boolean;
}

function toDisplay(value: number | null, kind: FieldKind): string {
  if (value == null || !Number.isFinite(value)) return "";
  if (kind === "pct") return (value * 100).toFixed(2);
  if (kind === "millions") return (value / 1e6).toFixed(0);
  return String(Math.round(value * 10000) / 10000);
}

function fromDisplay(text: string, kind: FieldKind): number | null {
  const parsed = parseFloat(text.replace(/,/g, ""));
  if (!Number.isFinite(parsed)) return null;
  if (kind === "pct") return parsed / 100;
  if (kind === "millions") return parsed * 1e6;
  return parsed;
}

const SUFFIX: Record<FieldKind, string> = { pct: "%", millions: "$M", raw: "" };

export function NumberField({ label, anchor, value, onChange, kind, missing }: Props) {
  const [text, setText] = useState(() => toDisplay(value, kind));
  const [focused, setFocused] = useState(false);

  // Adopt external updates (data load, reset) while the user isn't typing
  useEffect(() => {
    if (!focused) setText(toDisplay(value, kind));
  }, [value, kind, focused]);

  return (
    <div className="assumption">
      <div className="label">
        {label}
        {SUFFIX[kind] && <span className="muted"> ({SUFFIX[kind]})</span>}
        {anchor && <span className="anchor">{anchor}</span>}
      </div>
      <input
        className={missing && value == null ? "missing" : ""}
        value={text}
        onFocus={() => setFocused(true)}
        onBlur={() => {
          setFocused(false);
          setText(toDisplay(value, kind));
        }}
        onChange={(e) => {
          setText(e.target.value);
          onChange(fromDisplay(e.target.value, kind));
        }}
        placeholder={missing ? "required" : ""}
        inputMode="decimal"
      />
    </div>
  );
}

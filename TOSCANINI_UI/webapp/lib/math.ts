// The math-text splitter — the pure, deterministic half of the
// summary-surface equation renderer.
//
// Contract (all decisions mechanical, none interpretive):
//   - Display math:  $$…$$  and  \[…\]
//   - Inline math:   $…$    and  \(…\)
//   - An inline $…$ pair must be single-line, non-empty, and tight:
//     the opening $ is followed by a non-space, the closing $ is
//     preceded by a non-space (so "$5 and $6" is money, not math).
//   - Anything unbalanced or ambiguous stays PLAIN TEXT — a failure
//     to parse is never silently rendered as math (the honest
//     fallback: prose renders exactly as it did before).

export type MathSegment = {
  kind: "text" | "math";
  body: string;
  display: boolean;
};

type Delim = { open: string; close: string; display: boolean };

const DELIMS: Delim[] = [
  { open: "$$", close: "$$", display: true },
  { open: "\\[", close: "\\]", display: true },
  { open: "\\(", close: "\\)", display: false },
  { open: "$", close: "$", display: false },
];

/** Find the earliest math delimiter opening at or after `from`. */
function earliestOpen(text: string, from: number):
  { index: number; delim: Delim } | null {
  let best: { index: number; delim: Delim } | null = null;
  for (const d of DELIMS) {
    const idx = text.indexOf(d.open, from);
    if (idx === -1) continue;
    if (best === null || idx < best.index) best = { index: idx, delim: d };
  }
  return best;
}

/** True when an inline $…$ body satisfies the tightness rules. */
function tightDollar(text: string, open: number, close: number): boolean {
  const body = text.slice(open + 1, close);
  if (body.length === 0) return false;
  if (body.includes("\n")) return false;
  if (/\s/.test(body[0])) return false; // "$ x" → money, not math
  if (/\s/.test(body[body.length - 1])) return false; // "x $" → money
  return true;
}

/** Split prose into text / math segments. Never throws; never drops
 * characters: the concatenation of all bodies equals the input. */
export function splitMathSegments(text: string): MathSegment[] {
  const src = String(text ?? "");
  const out: MathSegment[] = [];
  let plainStart = 0;
  let i = 0;

  const pushText = (end: number) => {
    if (end > plainStart) {
      out.push({ kind: "text", body: src.slice(plainStart, end),
                 display: false });
    }
  };

  while (i < src.length) {
    const found = earliestOpen(src, i);
    if (!found) break;
    const { index, delim } = found;
    const bodyStart = index + delim.open.length;
    const closeIdx = src.indexOf(delim.close, bodyStart);
    if (closeIdx === -1) {
      // unbalanced opening → plain text from here; do not retry the
      // same delimiter family forever (advance past this opener)
      i = bodyStart;
      continue;
    }
    if (!delim.display && delim.open === "$"
        && !tightDollar(src, index, closeIdx)) {
      // money or stray $ — treat the opener as plain text
      i = bodyStart;
      continue;
    }
    const body = src.slice(bodyStart, closeIdx);
    if (body.trim().length === 0) {
      // empty math body — keep it as text (no zero-width artifacts)
      i = closeIdx + delim.close.length;
      continue;
    }
    pushText(index);
    out.push({ kind: "math", body, display: delim.display });
    i = closeIdx + delim.close.length;
    plainStart = i;
  }
  pushText(src.length);
  return out;
}

/** True when the text contains at least one renderable math segment. */
export function hasMath(text: string): boolean {
  return splitMathSegments(text).some((s) => s.kind === "math");
}

"use client";

// The summary-surface math renderer. Prose renders as prose; delimited
// math ($…$, $$…$$, \(…\), \[…\]) renders through KaTeX — loaded
// lazily ONLY when a math segment actually exists, so the bundle pays
// nothing for pages without equations. Until KaTeX arrives (or if it
// never can), the text renders exactly as before: a rendering layer
// that cannot load never changes the words (honest degradation).

import { useEffect, useState } from "react";
import { splitMathSegments, type MathSegment } from "@/lib/math";

type KatexModule = {
  renderToString: (
    tex: string,
    opts: Record<string, unknown>
  ) => string;
};

export default function MathText({
  text,
  className,
  as = "p",
}: {
  text: string;
  className?: string;
  as?: "p" | "span";
}) {
  const segments: MathSegment[] = splitMathSegments(text ?? "");
  const mathCount = segments.filter((s) => s.kind === "math").length;
  const [rendered, setRendered] = useState<string[] | null>(null);

  useEffect(() => {
    if (mathCount === 0) return;
    let alive = true;
    Promise.all([
      import("katex"),
      import("katex/dist/katex.min.css"),
    ])
      .then(([katexMod]) => {
        if (!alive) return;
        const katex: KatexModule = {
          renderToString: katexMod.default.renderToString,
        };
        setRendered(
          segments.map((seg) =>
            seg.kind === "math"
              ? katex.renderToString(seg.body, {
                  displayMode: seg.display,
                  throwOnError: false,
                  output: "html",
                })
              : ""
          )
        );
      })
      .catch(() => {
        /* stay plain — the words never change, only the typography */
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, mathCount]);

  if (mathCount === 0) {
    return as === "p"
      ? <p className={className}>{text}</p>
      : <span className={className}>{text}</span>;
  }

  const Tag = as === "p" ? "p" : "span";
  return (
    <Tag className={className} data-math-text>
      {segments.map((seg, i) => {
        if (seg.kind === "text") return <span key={i}>{seg.body}</span>;
        const cls = seg.display ? "math-display" : "math-inline";
        if (rendered && rendered[i]) {
          // KaTeX output (generated locally from the run's own
          // recorded text; throwOnError false, no input echo)
          return (
            <span
              key={i}
              className={cls}
              data-math
              dangerouslySetInnerHTML={{ __html: rendered[i] }}
            />
          );
        }
        // pre-load (or load-failure) fallback: the raw recorded text
        return (
          <span key={i} className={cls} data-math-pending>
            {seg.body}
          </span>
        );
      })}
    </Tag>
  );
}

"use client";

// R419 section 11: "What Toscanini invented" — the engineer's narrative
// in the CENTER pane. The same 8 sections the technology package PDF
// renders, built from the run's own canonical state (CIO + run record);
// raw machine state never leaks into the prose (the essay builder's
// own guard enforces it server-side; this component renders text only).

import { useEffect, useState } from "react";
import type { EssayBody } from "@/lib/types";
import { getEssay } from "@/lib/api";

const TITLES: Record<string, string> = {
  what_toscanini_invented: "What Toscanini invented",
  why_it_could_work: "Why it could work",
  what_is_genuinely_different: "What is genuinely different",
  frontier_capability_transferred: "Frontier capability transferred",
  evidence: "The evidence",
  what_remains_unknown: "What remains unknown",
  what_could_kill_it: "What could kill it",
  decisive_experiment: "The decisive experiment",
};

export default function InventionEssay({
  sessionId,
}: {
  sessionId: string;
}) {
  const [essay, setEssay] = useState<EssayBody | null>(null);
  const [open, setOpen] = useState(true);

  useEffect(() => {
    let alive = true;
    getEssay(sessionId)
      .then((e) => alive && setEssay(e))
      .catch(() => alive && setEssay(null));
    return () => {
      alive = false;
    };
  }, [sessionId]);

  if (!essay || !essay.sections) return null;
  const order = essay.section_order?.length
    ? essay.section_order
    : Object.keys(essay.sections);
  const entries = order
    .filter((k) => essay.sections[k])
    .map((k) => [k, essay.sections[k]] as const);
  if (entries.length === 0) return null;

  return (
    <div className="essay-block">
      <button
        type="button"
        className="essay-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span className="essay-title">The invention, in full</span>
        <span className="faint" style={{ fontSize: 11 }}>
          {open ? "hide" : "show"} · the 8-section technical narrative
          (same text as the package PDF)
        </span>
      </button>
      {open && (
        <div className="essay-sections">
          {entries.map(([key, text]) => (
            <section className="essay-section" key={key}>
              <h4>{TITLES[key] ?? key.replace(/_/g, " ")}</h4>
              <p>{text}</p>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

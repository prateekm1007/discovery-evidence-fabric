"use client";

// R395: the conversation's ask box — "Ask about this invention".
// Answers are AI_INTERPRETATION over the subject's OWN persisted
// artifacts; honest states (NOT_IN_RECORD, REFUSED_OVERCLAIM,
// TRANSPORT_ERROR, REFUSED) render as first-class answers, never as
// silent failures.

import { useState } from "react";
import type { AskResponse } from "@/lib/types";

export type AskMode = "run" | "invention";

function AnswerView({ a }: { a: AskResponse }) {
  if (a.status === "ANSWERED") {
    return (
      <div className="qa-answer">
        {a.answer}
        <div className="qa-meta faint">
          AI_INTERPRETATION · {a.basis}
        </div>
      </div>
    );
  }
  if (a.status === "NOT_IN_RECORD") {
    return (
      <div className="qa-answer qa-refusal">
        <b>Not in this record.</b>{" "}
        {a.answer?.replace(/^(\*\*)?NOT_IN_THIS_RECORD(\*\*)?\.?\s*/i, "") ??
          "The run's own artifacts do not contain the answer."}
        <div className="qa-meta faint">
          honest refusal — Toscanini answers only from this
          subject&apos;s persisted artifacts, never from world knowledge
        </div>
      </div>
    );
  }
  if (a.status === "REFUSED_OVERCLAIM") {
    return (
      <div className="qa-answer qa-refusal">
        <b>Refused by the reality guard.</b> {a.reason}
      </div>
    );
  }
  if (a.status === "TRANSPORT_ERROR") {
    return (
      <div className="qa-answer qa-refusal">
        <b>The model transport is not answering.</b> {a.reason}
        <div className="qa-meta faint">
          no fabricated answer is ever produced — retry when the
          transport responds
        </div>
      </div>
    );
  }
  return (
    <div className="qa-answer qa-refusal">
      <b>{a.status}.</b> {a.reason}
    </div>
  );
}

export default function AskBox({
  mode,
  subject,
  enabled,
  placeholder,
}: {
  mode: AskMode;
  subject: string; // run id or slot
  enabled: boolean;
  placeholder?: string;
}) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [answers, setAnswers] = useState<
    { question: string; response: AskResponse }[]
  >([]);

  async function ask() {
    const question = q.trim();
    if (!question || busy) return;
    setBusy(true);
    try {
      const { askRun, askInvention } = await import("@/lib/api");
      const response =
        mode === "run"
          ? await askRun(subject, question)
          : await askInvention(subject, question);
      setAnswers((prev) => [...prev, { question, response }]);
      setQ("");
    } catch (e) {
      setAnswers((prev) => [
        ...prev,
        {
          question,
          response: {
            status: "TRANSPORT_ERROR",
            reason: e instanceof Error ? e.message : "request failed",
          },
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="askbox">
      {answers.length > 0 && (
        <div className="qa-thread">
          {answers.map((a, i) => (
            <div className="qa-pair" key={i}>
              <div className="qa-question">{a.question}</div>
              <AnswerView a={a.response} />
            </div>
          ))}
        </div>
      )}
      <div className="qa-inputrow">
        <input
          className="qa-input"
          placeholder={
            placeholder ??
            (enabled
              ? "Ask about this invention — answered from its own record…"
              : "available when the run finishes")
          }
          value={q}
          disabled={!enabled || busy}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void ask();
            }
          }}
        />
        <button
          className="btn small"
          onClick={() => void ask()}
          disabled={busy || !enabled || !q.trim()}
          type="button"
        >
          {busy ? "Thinking…" : "Ask"}
        </button>
      </div>
      <div className="qa-foot faint">
        answers are AI interpretation of the subject&apos;s own
        artifacts — unknowns stay unknown, nothing claims physical
        validation
      </div>
    </div>
  );
}

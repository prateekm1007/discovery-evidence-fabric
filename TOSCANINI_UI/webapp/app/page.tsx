"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listSessions, listShowcase, startRun } from "@/lib/api";
import type { SessionRow, ShowcaseRow } from "@/lib/types";

const EXAMPLES = [
  "Why do infusion pumps fail to detect downstream occlusion before patient harm?",
  "How can EV traction-battery thermal runaway initiation be prevented?",
  "Why do rails fracture in service under fatigue loading?",
  "How can we keep minimum drainage when a shunt's primary lumen obstructs?",
];

function statusClass(status: string): string {
  if (status.startsWith("ERROR")) return "ERROR";
  return status;
}

export default function Home() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [showcase, setShowcase] = useState<ShowcaseRow[]>([]);

  useEffect(() => {
    listSessions().then(setSessions).catch(() => setSessions([]));
    listShowcase().then(setShowcase).catch(() => setShowcase([]));
  }, []);

  async function submit() {
    const t = text.trim();
    if (t.length < 15) {
      setError("Please describe the problem in a bit more detail (at least 15 characters).");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const session = await startRun(t);
      router.push(`/run/${session.session_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to start the run");
      setBusy(false);
    }
  }

  const focus = showcase.filter((s) => s.demo_focus);
  const others = showcase.filter((s) => !s.demo_focus);

  return (
    <main>
      <section className="hero">
        <h1>
          Describe an engineering or scientific problem.
          <br />
          Get a technology package you can act on.
        </h1>
        <p className="lede">
          Toscanini runs a real discovery engine — evidence first, adversarial
          attacks included — and returns a mechanism, an inspectable 3D design,
          a decisive experiment, and a downloadable buyer dossier.
        </p>

        <div className="ask">
          <textarea
            placeholder="e.g. Why do hemodialysis grafts clot at the venous anastomosis despite anticoagulation?"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
            }}
          />
          <div className="ask-foot">
            <span className="hint">
              ⌘↵ to start · runs take minutes; you can leave and come back
            </span>
            <button className="btn" onClick={submit} disabled={busy}>
              {busy ? "Starting…" : "Start discovery"}
            </button>
          </div>
        </div>

        {error && <div className="errbox" style={{ textAlign: "left" }}>{error}</div>}

        <div className="examples">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              className="example"
              onClick={() => setText(ex)}
              type="button"
            >
              {ex.length > 62 ? ex.slice(0, 60) + "…" : ex}
            </button>
          ))}
        </div>
      </section>

      {sessions.length > 0 && (
        <section className="section">
          <h2>Your runs</h2>
          <div className="sub">Real engine runs, artifact-derived statuses</div>
          <div className="history">
            {sessions.slice(0, 12).map((s) => (
              <a className="run-row" href={`/run/${s.session_id}`} key={s.session_id}>
                <span className={`pill ${statusClass(s.status)}`}>{s.status}</span>
                <span className="title">{s.title}</span>
                <span className="when">
                  {s.final_status ? `${s.final_status} · ` : ""}
                  {s.created_at?.slice(0, 16).replace("T", " ")}
                </span>
              </a>
            ))}
          </div>
        </section>
      )}

      {focus.length > 0 && (
        <section className="section">
          <h2>Technology packages</h2>
          <div className="sub">
            Built by the same engine, released through the certified chain —
            inspect them end-to-end, including the interactive 3D design
          </div>
          <div className="gallery">
            {focus.map((s) => (
              <a className="card" href={`/showcase/${s.slot}`} key={s.slot}>
                <div className="kicker">
                  {s.domain} · {s.package_id}
                </div>
                <h3>{s.title}</h3>
                <p>{s.blurb}</p>
                <div className="foot">
                  {s.parameter_count} live parameters · interactive 3D
                </div>
              </a>
            ))}
          </div>
          {others.length > 0 && (
            <div className="examples" style={{ justifyContent: "flex-start", marginTop: 16 }}>
              {others.map((s) => (
                <a className="example" href={`/showcase/${s.slot}`} key={s.slot}>
                  {s.title}
                </a>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}

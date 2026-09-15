"use client";

// R459 (audit P1-3): the public read-only share view — an
// unauthenticated visitor opening /share?id={id} sees the discovery's
// summary, outcome, and evidence sample. Nothing here offers mutation;
// steering stays owner-only by construction.
// (Query-param route: the static export cannot prerender path params.)
//
// R461 (independent audit P0-3, reproduced live): the page previously
// rendered the R459 ASSUMED payload shape (problem as a string,
// outcome_label / decision / evidence_titles). The backend's real
// share payload (GET /api/share/{id}) serves problem as an OBJECT
// ({title, failure_mode, domain}) plus invention / evidence /
// key_uncertainty / package_availability — rendering an object as a
// React child crashes the client (React error #31, the auditor's
// "share links crash during client rendering"; the R460 route fix made
// the shell serve but the client still crashed). This view now renders
// the REAL contract, defensively: every interpolated value passes
// through a text guard, so a shape drift degrades to honest absence —
// never a crash. The maturity boundary is first-line (P1-10): the
// epistemic class renders in the same line as the outcome, and the
// read-only nature is the first thing the visitor reads (the audit's
// sharing moment: "Can a colleague open this without my session? Is
// it read-only?").

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { presentMaturity } from "@/lib/present";

interface SharePayload {
  problem?: unknown;
  invention?: unknown;
  evidence?: unknown;
  key_uncertainty?: unknown;
  package_availability?: unknown;
  created_at?: unknown;
  [k: string]: unknown;
}

/** The only way a payload value becomes a React child: it is a string.
 * Anything else (objects, arrays, numbers from schema drift) renders
 * as honest absence — a shape drift must degrade, never crash. */
function asText(v: unknown): string | null {
  return typeof v === "string" && v.trim() ? v : null;
}

/** problem arrives as {title, failure_mode, domain} (current backend)
 * or a plain string (the R459 shape, kept for compatibility). */
function problemTitle(problem: unknown): string | null {
  if (typeof problem === "string" && problem.trim()) return problem;
  if (problem && typeof problem === "object") {
    const t = (problem as { title?: unknown }).title;
    return asText(t);
  }
  return null;
}

function stringList(v: unknown): string[] {
  return Array.isArray(v)
    ? v.filter((x): x is string => typeof x === "string")
    : [];
}

/** The canonical outcome words for the statuses this endpoint serves —
 * the same vocabulary as toscanini/user_state.py::FINAL_STATUS_READABLE
 * (one wording, duplicated at the static-export boundary by necessity;
 * the comment binds them — drift here is a defect, Art. X). */
const SHARE_STATUS_READABLE: Record<string, string> = {
  AUTOMATED_INVENTION_CANDIDATE: "Invention candidate (automated)",
  EVOLVED_INVENTION_CANDIDATE: "Evolved invention candidate",
  INVENTION_UNDER_DEVELOPMENT: "Invention in development",
  MECHANISM_GENERATION_FAILED:
    "Mechanism generation failed (a generation gap — not a rejection)",
  REJECTED:
    "Challenged and killed — the generation record shows the diagnosed cause",
  MALFORMED_OR_FALSE_PREMISE:
    "False premise — the problem as stated cannot physically occur",
  UNKNOWN: "Outcome unknown",
};

function outcomeLine(invention: unknown): string {
  const inv = (invention ?? {}) as { status?: unknown };
  const status = asText(inv.status) ?? "";
  return SHARE_STATUS_READABLE[status] ?? "Investigation record";
}

function ShareView() {
  const params = useSearchParams();
  const id = params.get("id");
  const [data, setData] = useState<SharePayload | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    if (!id) return;
    fetch(`/api/share/${id}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("404"))))
      .then(setData)
      .catch(() => setMissing(true));
  }, [id]);

  const invention = (data?.invention ?? {}) as Record<string, unknown>;
  const evidence = (data?.evidence ?? {}) as Record<string, unknown>;
  const pkg = (data?.package_availability ?? {}) as {
    available?: unknown;
    maturity?: unknown;
  };
  const problem = data ? problemTitle(data.problem) : null;
  const mechanism = asText(invention.mechanism);
  const why = asText(invention.why_it_may_work);
  const uncertainty = asText(data?.key_uncertainty);
  const maturity = presentMaturity(
    asText(invention.epistemic_class) ??
      (typeof pkg.maturity === "string" ? pkg.maturity : null)
  );
  const titles = stringList(evidence.records);
  const sources = stringList(evidence.sources_queried);
  const pkgAvailable = pkg.available === true;

  return (
    <main className="share-page" data-share-page>
      <a className="brand" href="/">
        Toscanini
      </a>
      {!id && (
        <div className="errbox" style={{ marginTop: 24 }}>
          This share address is missing its identifier — ask the person
          who shared it for a fresh link.
        </div>
      )}
      {id && missing && (
        <div className="errbox" style={{ marginTop: 24 }}>
          <b>This share link is not valid.</b> It may have been revoked, or
          the address is incomplete — ask the person who shared it for a
          fresh link.
        </div>
      )}
      {id && !missing && !data && (
        <div className="loading">Opening the shared discovery…</div>
      )}
      {id && data && (
        <div className="share-body">
          <div className="share-outcome" data-share-outcome>
            Read-only snapshot · {outcomeLine(invention)}
          </div>
          <h1 className="share-problem">
            {problem ?? "Shared discovery"}
          </h1>
          {maturity && (
            <p className="share-maturity" data-share-maturity>
              {maturity}
            </p>
          )}
          {mechanism && (
            <section className="share-sec">
              <h2>The mechanism under investigation</h2>
              <p>{mechanism}</p>
            </section>
          )}
          {why && mechanism !== why && (
            <section className="share-sec">
              <h2>Why it may work</h2>
              <p>{why}</p>
            </section>
          )}
          {uncertainty && (
            <section className="share-sec">
              <h2>What remains uncertain</h2>
              <p>{uncertainty}</p>
            </section>
          )}
          {titles.length > 0 && (
            <section className="share-sec">
              <h2>What the investigation read</h2>
              <ul>
                {titles.slice(0, 12).map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
              {sources.length > 0 && (
                <div className="share-sources faint">
                  Evidence from {sources.join(", ")}
                </div>
              )}
            </section>
          )}
          {!pkgAvailable && (
            <div className="share-sources faint" data-share-nopackage>
              No technology package is attached to this record — the
              investigation did not reach package delivery.
            </div>
          )}
          <div className="share-foot faint">
            A read-only record of one investigation — outcomes are stated
            exactly as recorded; nothing here claims physical validation.
          </div>
        </div>
      )}
    </main>
  );
}

export default function SharePage() {
  return (
    <Suspense fallback={<div className="loading">Loading…</div>}>
      <ShareView />
    </Suspense>
  );
}

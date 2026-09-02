"use client";

// The engineering argument — R389 Phase 4 baseline, R395 the CEO's
// nine-field form. Derived ONLY from the run's persisted artifacts
// (never private chain-of-thought): Problem / Evidence / Hypothesis /
// Design decision / Result / Challenge / Reality / Decision / Next
// decisive experiment. Absent fields say so honestly — never
// synthesized (Art. XXV).

import type { SessionDetail, StageDigest } from "@/lib/types";

function str(x: unknown, max = 400): string {
  if (x == null) return "";
  if (typeof x === "string") return x;
  if (typeof x === "number" || typeof x === "boolean") return String(x);
  try {
    return JSON.stringify(x).slice(0, max);
  } catch {
    return String(x);
  }
}

function pick(obj: Record<string, unknown> | null | undefined, key: string) {
  if (!obj) return undefined;
  return obj[key];
}

export function EngineeringArgument({
  detail,
}: {
  detail: NonNullable<SessionDetail>;
}) {
  const inv = (detail.invention_specification ??
    {}) as Record<string, unknown>;
  const invMech = pick(inv, "mechanism") as Record<string, unknown> | undefined;
  const invCausal = pick(inv, "causal_chain") as
    | Record<string, unknown>
    | undefined;
  const invNovelty = pick(inv, "novelty_hypothesis") as
    | Record<string, unknown>
    | undefined;
  const unc = pick(inv, "uncertainties");
  const ke = (detail.decisive_experiment ?? {}) as Record<string, unknown>;
  const keSel = (ke.selected ?? ke) as Record<string, unknown>;
  const fs = (detail.final_state ?? {}) as Record<string, unknown>;
  const pkg = detail.package ?? null;
  const usv = detail.user_state_view;
  const epRetrieval = detail.evidence_pack?.retrieval ?? [];

  const synthesizeStage = detail.stages?.find((s) => s.stage === "SYNTHESIZE");
  const retrieveStage = detail.stages?.find((s) => s.stage === "RETRIEVE");
  const attackStage = detail.stages?.find((s) => s.stage === "ATTACK");
  const challenges = (attackStage?.challenges ?? []).slice(0, 3);

  const decision = usv?.found_something
    ? "KEEP — a candidate survived the adversarial chain"
    : usv?.rejected
      ? "KILL — the candidate was not defensible enough to package; recorded to the mechanism cemetery"
      : str(fs.final_status, 200) || "outcome not established";

  const Step = ({
    k,
    children,
  }: {
    k: string;
    children: React.ReactNode;
  }) => (
    <div className="step">
      <div className="k">{k}</div>
      <div className="v">{children}</div>
    </div>
  );

  return (
    <div className="arg">
      <Step k="Problem">
        {detail.title}
      </Step>
      <Step k="Evidence">
        {(epRetrieval.length > 0
          ? epRetrieval.slice(0, 4).map((r, i) => (
              <div key={i}>
                · <b>{r.source ?? "?"}</b> — {str(r.title, 160)}
              </div>
            ))
          : (retrieveStage?.sample_titles ?? []).map((t, i) => (
              <div key={i}>· {t}</div>
            ))) || (
          <span className="faint">no retrieval evidence displayed</span>
        )}
        <div className="faint">
          {retrieveStage?.records_found ?? 0} records · custody-frozen
          with content hashes
        </div>
      </Step>
      <Step k="Hypothesis">
        {str(invMech?.value ?? synthesizeStage?.mechanism, 500) || (
          <span className="faint">not established by this run</span>
        )}
      </Step>
      <Step k="Design decision">
        {str(invCausal?.value ?? synthesizeStage?.intervention, 500) || (
          <span className="faint">not established by this run</span>
        )}
      </Step>
      <Step k="Result">
        {str(fs.final_status, 300) || detail.final_status || (
          <span className="faint">pending</span>
        )}
        {pkg?.maturity && (
          <div className="faint">package maturity: {pkg.maturity}</div>
        )}
      </Step>
      <Step k="Challenge">
        {challenges.length > 0 ? (
          challenges.map((c, i) => (
            <div key={i}>
              · {str(c.challenge ?? c.verdict, 200)}
              {c.verdict ? (
                <span className="faint"> — {c.verdict}</span>
              ) : null}
            </div>
          ))
        ) : attackStage?.overall ? (
          <>Adversarial gate: {attackStage.overall}</>
        ) : (
          <span className="faint">
            no adversarial attack recorded on this run
          </span>
        )}
      </Step>
      <Step k="Reality">
        {usv?.package_available ? (
          <>
            This run produced a computationally-validated technology
            package. No physical observation exists anywhere in this
            program&apos;s records — every result is
            COMPUTATIONAL_RESULT or MODELLED, stated as such.
          </>
        ) : (
          <span className="faint">
            simulated / modelled results only — nothing on this run was
            measured in reality (the honest state, never hidden)
          </span>
        )}
      </Step>
      <Step k="Decision">{decision}</Step>
      <Step k="Next decisive experiment">
        {str(keSel.name ?? keSel.description, 400) || (
          <span className="faint">
            the decisive experiment stage will appear here
          </span>
        )}
      </Step>
    </div>
  );
}

export function NoveltyAndCemetery({
  detail,
}: {
  detail: NonNullable<SessionDetail>;
}) {
  const inv = (detail.invention_specification ??
    {}) as Record<string, unknown>;
  const invNovelty = pick(inv, "novelty_hypothesis") as
    | Record<string, unknown>
    | undefined;

  function CemeteryBlock({ update }: { update: unknown }) {
    const app = ((update as Record<string, unknown>)?.appended ??
      update) as Record<string, unknown>;
    const proposed = String(
      app.what_was_proposed ?? app.mechanism_name ?? ""
    );
    const why = String(app.why_it_failed ?? app.kill_reason ?? "").trim();
    const lesson = String(app.reusable_lesson ?? "").trim();
    const entryId = String(app.entry_id ?? "");
    const total = (update as Record<string, unknown>)?.total_entries;
    if (!proposed && !why && !entryId) {
      return <li style={{ fontSize: 13.5 }}>{str(update, 400)}</li>;
    }
    return (
      <li style={{ fontSize: 13.5, lineHeight: 1.55 }}>
        {proposed && (
          <>
            Killed and recorded: <b>{proposed}</b>
            {why && ` — ${why}`}
            {lesson && `. Lesson kept: ${lesson}`}
            .
          </>
        )}
        <div className="faint" style={{ marginTop: 5, fontSize: 12 }}>
          negative knowledge — the cemetery is append-only
          {total != null ? ` (${total} entries)` : ""}
          {entryId ? ` · ${entryId}` : ""}
        </div>
      </li>
    );
  }

  return (
    <div className="grid2">
      <div className="block">
        <h4>Novelty hypothesis</h4>
        <div style={{ fontSize: 14 }}>
          {str(invNovelty?.value, 600) || "not established"}
        </div>
      </div>
      <div className="block">
        <h4>Cemetery update (negative knowledge)</h4>
        <ul>
          {detail.cemetery_update ? (
            <CemeteryBlock update={detail.cemetery_update} />
          ) : (
            <li>
              no cemetery entry from this run{" "}
              <span className="faint">
                (only kills and rejects are recorded — kept forever)
              </span>
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}

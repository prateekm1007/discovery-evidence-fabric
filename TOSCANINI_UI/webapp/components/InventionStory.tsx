"use client";

// R395: the workspace's center pane for a RELEASED INVENTION — the
// technology's story in the buyer chain's own words: what it does, why
// it matters, what is established / not established, what could kill
// it, the decisive experiment, the reality loop, and the equations.
// Brief sections are extracted verbatim from the released executive
// brief PDFs (Art. XXXIX — the buyer chain's own words).

import type { RealityLoopRecord, ShowcaseDetail } from "@/lib/types";
import RealityLoopPanel from "./RealityLoopPanel";

export default function InventionStory({
  detail,
  loop,
}: {
  detail: ShowcaseDetail;
  loop: RealityLoopRecord | null;
}) {
  const brief = detail.brief ?? {};
  const ecc = detail.evidence_class_counts ?? {};

  return (
    <>
      <div className="problem">
        <div className="label">
          {detail.package_id} · technology package · from the certified
          buyer-distribution chain
        </div>
        <div className="text" style={{ fontFamily: "var(--serif)", fontSize: 22 }}>
          {detail.title}
        </div>
        {detail.blurb && <div className="sub">{detail.blurb}</div>}
      </div>

      {(brief.what_it_does || detail.mechanism_summary) && (
        <section className="section briefsec">
          <h2>What it does</h2>
          <div className="sub">from the released executive brief</div>
          {brief.what_it_does && (
            <p className="brieflead">{brief.what_it_does}</p>
          )}
          {detail.mechanism_summary && (
            <p className="briefbody">
              <b>The engineering model:</b> {detail.mechanism_summary}
            </p>
          )}
        </section>
      )}

      {brief.why_it_matters && (
        <section className="section briefsec">
          <h2>Why it matters</h2>
          <div className="sub">the recorded problem, with its sources</div>
          <p className="briefbody">{brief.why_it_matters}</p>
        </section>
      )}

      {(detail.maturity || brief.established) && (
        <section className="section briefsec">
          <h2>Key technical result</h2>
          <div className="sub">what is actually established</div>
          <div className="resultgrid">
            {detail.maturity && (
              <span className="pill COMPLETE">{detail.maturity}</span>
            )}
            {detail.loop_verification_state && (
              <span className="pill RUNNING">
                loop state: {detail.loop_verification_state}
              </span>
            )}
          </div>
          {brief.established && (
            <p className="briefbody">{brief.established}</p>
          )}
        </section>
      )}

      {(Object.keys(ecc).length > 0 || brief.established) && (
        <section className="section briefsec">
          <h2>Evidence</h2>
          <div className="sub">honest evidence classes — nothing hidden</div>
          <div className="chainpills">
            {Object.entries(ecc).map(([cls, n]) => (
              <span className="chainpill" key={cls}>
                {cls.replace(/_/g, " ")}: {String(n)}
              </span>
            ))}
          </div>
          <p className="brieffoot">
            Every claim traces to its recorded evidence span. The full
            evidence summary, traceability records, and each source citation
            are inside the downloadable package.
          </p>
        </section>
      )}

      {(brief.kill_condition || brief.not_established) && (
        <section className="section briefsec">
          <h2>What could kill it</h2>
          <div className="sub">
            stated before you buy — the design&apos;s own recorded kill
            condition
          </div>
          {brief.kill_condition && (
            <div className="killbox">
              <b>Kill condition:</b> {brief.kill_condition}
            </div>
          )}
          {brief.not_established && (
            <p className="briefbody">{brief.not_established}</p>
          )}
          {(detail.known_blockers ?? []).length > 0 && (
            <details className="tech">
              <summary>All recorded blockers and unknowns</summary>
              <ul>
                {(detail.known_blockers ?? []).map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}

      {(brief.decisive_experiment ||
        detail.first_decisive_work_package?.work_package) && (
        <section className="section briefsec">
          <h2>Decisive experiment</h2>
          <div className="sub">
            the first thing the buyer runs — it can falsify the mechanism
          </div>
          {brief.decisive_experiment && (
            <p className="brieflead">{brief.decisive_experiment}</p>
          )}
          {detail.first_decisive_work_package?.recorded_effort && (
            <p className="brieffoot">
              Recorded effort:{" "}
              {detail.first_decisive_work_package.recorded_effort}
            </p>
          )}
        </section>
      )}

      {loop && <RealityLoopPanel record={loop} />}

      {detail.equations.length > 0 && (
        <section className="section briefsec">
          <h2>Engineering equations</h2>
          <div className="sub">the closed-form relations bound to this design</div>
          <div className="params">
            {detail.equations.map((e, i) => (
              <div className="param" key={i}>
                <div className="pid" style={{ fontSize: 14 }}>
                  {e.expression}
                </div>
                {e.caption && (
                  <div className="basis" style={{ marginTop: 6 }}>
                    {e.caption}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <p className="brieffoot">
        {detail.provenance_note}{" "}
        {brief.source
          ? ` Brief sections extracted verbatim from ${brief.source}.`
          : ""}
      </p>
    </>
  );
}

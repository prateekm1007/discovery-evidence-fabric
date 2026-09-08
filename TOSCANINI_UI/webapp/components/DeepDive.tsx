"use client";

// R435 — the DEEP LAYER: every rigorous surface, progressively
// disclosed under the technology stage.
//
//   Investigation journal   phases · generations · the engineering
//                           argument · the essay · the full event
//                           history with per-event provenance
//   Summary                 the problem, mechanism, evidence, unknowns
//   The technology model    components · generation history · the three
//                           separated quality scores · model identity ·
//                           gates · parameters · renders
//   Evidence                the full ledger — used vs retrieved
//   Engineering             parameters, traceability, build steps
//   The decisive test       the buyer-runnable falsification contract
//   The technology package  what the ZIP carries · download
//   Ask a question          answered from this run's own records
//
// Sections are collapsed by default (complexity is revealed when asked
// for, never upfront). Engine vocabulary (epistemic classes, stage
// names, provenance refs) lives HERE — the deep layer — where rigor
// belongs, never on the stage surface.

import { useEffect, useRef, useState } from "react";
import type {
  DossierBody,
  DossierTab,
  GauntletCard,
  ScienceEvent,
  SessionDetail,
} from "@/lib/types";
import RunNarrative from "./RunNarrative";
import {
  EngineeringArgument,
  NoveltyAndCemetery,
} from "./EngineeringArgument";
import InventionEssay from "./InventionEssay";
import AskBox from "./AskBox";
import { Gauntlet, ScienceEventStream } from "./ScienceEvents";
import {
  EvidenceSection,
  EngineeringSection,
  ExperimentSection,
  FalsificationCard,
  ModelDetailsSection,
  PackageSection,
  SummarySection,
} from "./DossierSections";
import type { DesignTabData } from "./DossierSections";

type SectionId =
  | "journal"
  | "summary"
  | "model"
  | "evidence"
  | "engineering"
  | "experiment"
  | "package"
  | "ask";

const SECTIONS: { id: SectionId; title: string; sub: string }[] = [
  {
    id: "journal",
    title: "Investigation journal",
    sub: "phases, generations, the engineering argument, the full event history",
  },
  {
    id: "summary",
    title: "Summary",
    sub: "the problem, the mechanism, evidence and unknowns",
  },
  {
    id: "model",
    title: "The technology model",
    sub: "components, generation history, quality scores, identity, parameters",
  },
  {
    id: "evidence",
    title: "Evidence",
    sub: "the full ledger — what was retrieved and what shaped the design",
  },
  {
    id: "engineering",
    title: "Engineering",
    sub: "parameters, traceability, build steps",
  },
  {
    id: "experiment",
    title: "The decisive test",
    sub: "the falsification experiment a buyer can run",
  },
  {
    id: "package",
    title: "The technology package",
    sub: "what the ZIP carries",
  },
  {
    id: "ask",
    title: "Ask a question",
    sub: "answered from this investigation's own records — or an honest refusal",
  },
];

function Section({
  id,
  title,
  sub,
  open,
  onToggle,
  children,
}: {
  id: SectionId;
  title: string;
  sub: string;
  open: boolean;
  onToggle: (id: SectionId, open: boolean) => void;
  children?: React.ReactNode;
}) {
  const ref = useRef<HTMLDetailsElement>(null);
  return (
    <details
      className="dd-sec"
      data-dd-section={id}
      ref={ref}
      open={open}
      onToggle={(e) => onToggle(id, (e.target as HTMLDetailsElement).open)}
    >
      <summary>
        <span className="dd-title">{title}</span>
        <span className="dd-sub faint">{sub}</span>
      </summary>
      <div className="dd-body">{children}</div>
    </details>
  );
}

export default function DeepDive({
  dossier,
  detail,
  events,
  gauntlet,
  packageAvailable,
  focusRequest,
  viewingGen,
  onSelectGen,
  highlight,
  onHighlight,
}: {
  dossier: DossierBody | null;
  detail: SessionDetail;
  events: ScienceEvent[];
  gauntlet: GauntletCard[];
  packageAvailable: boolean;
  focusRequest: string | null;
  viewingGen: number | null;
  onSelectGen: (gen: number | null) => void;
  highlight: string | null;
  onHighlight: (id: string | null) => void;
}) {
  const [open, setOpen] = useState<Set<SectionId>>(new Set());
  const refs = useRef<Record<string, HTMLElement | null>>({});

  // a focus request ("section:ts") opens that section and scrolls to it
  useEffect(() => {
    if (!focusRequest) return;
    const [sec] = focusRequest.split(":");
    if (!SECTIONS.some((s) => s.id === sec)) return;
    setOpen((prev) => new Set(prev).add(sec as SectionId));
    // let the browser paint the opened section before scrolling
    const t = setTimeout(() => {
      refs.current[sec]?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 60);
    return () => clearTimeout(t);
  }, [focusRequest]);

  function toggle(id: SectionId, isOpen: boolean) {
    setOpen((prev) => {
      const next = new Set(prev);
      if (isOpen) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  const done = detail.status === "COMPLETE";
  const tabs = dossier?.tabs;

  // journal content availability
  const hasJournal =
    events.length > 0 || gauntlet.length > 0 || detail.stages != null;

  return (
    <div className="deep-dive" data-deep-dive>
      <div className="dd-head faint">
        Under the surface — the full record: every claim, every class,
        every provenance trail
      </div>
      {SECTIONS.map((s) => {
        const body = (
          <div
            ref={(el) => {
              refs.current[s.id] = el;
            }}
          >
            {s.id === "journal" && (
              <>
                {hasJournal ? (
                  <>
                    <RunNarrative
                      detail={detail}
                      packageAvailable={packageAvailable}
                    />
                    {done && (
                      <>
                        <div className="dd-part">
                          <h3>The engineering argument</h3>
                          <div className="sub">
                            derived from the run&apos;s persisted
                            artifacts — evidence, mechanisms, decisions,
                            and what is still unknown
                          </div>
                          <EngineeringArgument
                            detail={detail}
                            packageAvailable={packageAvailable}
                          />
                        </div>
                        <div className="dd-part">
                          <InventionEssay sessionId={detail.session_id} />
                        </div>
                        <div className="dd-part">
                          <NoveltyAndCemetery detail={detail} />
                        </div>
                      </>
                    )}
                    {gauntlet.length > 0 && (
                      <div className="dd-part">
                        <h3>Scientific gauntlet</h3>
                        <Gauntlet cards={gauntlet} />
                      </div>
                    )}
                    {events.length > 0 && (
                      <div className="dd-part">
                        <h3>Event history</h3>
                        <div className="sub">
                          {events.length} recorded events — each carries
                          its own provenance; expand any card
                        </div>
                        <ScienceEventStream events={events} />
                      </div>
                    )}
                  </>
                ) : (
                  <div className="tab-note tn-pending">
                    No recorded events yet — the journal fills as the
                    investigation runs.
                  </div>
                )}
              </>
            )}
            {s.id === "summary" &&
              (tabs ? (
                <>
                  <SummarySection tab={tabs.overview as DossierTab} gauntlet={[]} />
                </>
              ) : (
                <div className="tab-note tn-pending">
                  The summary appears as soon as the investigation has a
                  canonical state.
                </div>
              ))}
            {s.id === "model" &&
              (tabs ? (
                <ModelDetailsSection
                  tab={tabs.design as DossierTab}
                  viewingGen={viewingGen}
                  onSelectGen={onSelectGen}
                  highlight={highlight}
                  onHighlight={onHighlight}
                />
              ) : (
                <div className="tab-note tn-pending">
                  Model details appear once geometry exists.
                </div>
              ))}
            {s.id === "evidence" &&
              (tabs ? (
                <EvidenceSection tab={tabs.evidence as DossierTab} />
              ) : (
                <div className="tab-note tn-pending">
                  The evidence ledger appears as sources are retrieved.
                </div>
              ))}
            {s.id === "engineering" &&
              (tabs ? (
                <EngineeringSection tab={tabs.engineering as DossierTab} />
              ) : (
                <div className="tab-note tn-pending">
                  Engineering details appear when the design reaches the
                  engineering stage.
                </div>
              ))}
            {s.id === "experiment" &&
              (tabs ? (
                <ExperimentSection tab={tabs.experiment as DossierTab} />
              ) : (
                <div className="tab-note tn-pending">
                  The decisive test is specified once the invention
                  survives its challenges.
                </div>
              ))}
            {s.id === "package" &&
              (tabs ? (
                <>
                  <PackageSection tab={tabs.transfer as DossierTab} />
                  {dossier?.falsification && (
                    <div className="dd-part">
                      <FalsificationCard f={dossier.falsification} />
                    </div>
                  )}
                  <div className="dossier-foot faint">
                    {dossier?.derived_from}
                  </div>
                </>
              ) : (
                <div className="tab-note tn-pending">
                  Package details appear when a package exists on this run.
                </div>
              ))}
            {s.id === "ask" && (
              <AskBox
                mode="run"
                subject={detail.session_id}
                enabled={done}
                placeholder="Ask about this investigation — answered from its own records, or an honest refusal"
              />
            )}
          </div>
        );
        return (
          <Section
            key={s.id}
            id={s.id}
            title={s.title}
            sub={s.sub}
            open={open.has(s.id)}
            onToggle={toggle}
          >
            {body}
          </Section>
        );
      })}
    </div>
  );
}

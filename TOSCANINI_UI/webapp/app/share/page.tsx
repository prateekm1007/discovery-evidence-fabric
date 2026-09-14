"use client";

// R459 (audit P1-3): the public read-only share view. The backend
// share endpoints existed (POST /api/sessions/{id}/share creates a
// consent-scoped link; GET /api/share/{share_id} serves a public
// payload) — this page makes them a product surface: an
// unauthenticated visitor opening /share?id={id} sees the discovery's
// summary, outcome, and evidence sample. Nothing here offers mutation;
// steering stays owner-only by construction.
// (Query-param route: the static export cannot prerender path params.)

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

interface SharePayload {
  problem?: string;
  outcome_label?: string;
  decision?: string;
  evidence_sources?: string[];
  evidence_titles?: string[];
  created_at?: string;
  [k: string]: unknown;
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
            {data.outcome_label || "Investigation record"}
          </div>
          <h1 className="share-problem">
            {data.problem || "Shared discovery"}
          </h1>
          {data.decision ? <p className="share-decision">{data.decision}</p> : null}
          {(data.evidence_sources?.length ?? 0) > 0 && (
            <div className="share-sources faint">
              Evidence from {(data.evidence_sources ?? []).join(", ")}
            </div>
          )}
          {(data.evidence_titles?.length ?? 0) > 0 && (
            <div className="share-titles">
              <h2>What the investigation read</h2>
              <ul>
                {(data.evidence_titles ?? []).slice(0, 12).map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
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

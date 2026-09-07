"use client";

// R419 (operator directive sections 5/8): the presentation render
// gallery — hero / section / exploded studio renders beside the
// interactive 3D. Every URL comes from the CIO's own
// visualization.renders pointers (the canonical object); the gallery
// never infers availability, never fabricates an image, and the
// section/exploded variants are labeled as PRESENTATION variants
// (Blender never alters the engineering truth — the authority is the
// CadQuery/OCCT GLB the viewer above serves).

import { useState } from "react";

export interface RenderEntry {
  key: string;
  url: string;
  title: string;
  caption: string;
}

export default function RenderGallery({
  renders,
  conceptual,
}: {
  renders: NonNullable<
    NonNullable<import("@/lib/types").CIO>["visualization"]
  >["renders"];
  conceptual: boolean;
}) {
  const entries: RenderEntry[] = [];
  if (renders?.hero_png) {
    entries.push({
      key: "hero",
      url: renders.hero_png,
      title: "Hero",
      caption: "the whole architecture, studio-lit",
    });
  }
  if (renders?.section_png) {
    entries.push({
      key: "section",
      url: renders.section_png,
      title: "Section",
      caption: "a presentation cut — see inside",
    });
  }
  if (renders?.exploded_png) {
    entries.push({
      key: "exploded",
      url: renders.exploded_png,
      title: "Exploded",
      caption: "components separated — how it comes apart",
    });
  }
  if (entries.length === 0) {
    // typed honest absence: the render stage did not produce artifacts
    // (no pinned build / timeout / failure) — the interactive GLB is
    // unaffected and that stays the contract
    return null;
  }
  const [sel, setSel] = useState(entries[0].key);
  const current = entries.find((e) => e.key === sel) ?? entries[0];

  return (
    <div className="render-gallery">
      <div className="gallery-tabs" role="tablist" aria-label="studio renders">
        {entries.map((e) => (
          <button
            key={e.key}
            type="button"
            role="tab"
            aria-selected={e.key === sel}
            className={`gallery-tab ${e.key === sel ? "sel" : ""}`}
            onClick={() => setSel(e.key)}
          >
            {e.title}
          </button>
        ))}
      </div>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        className="gallery-img"
        src={current.url}
        alt={`${current.title} studio render of the invention`}
      />
      <div className="gallery-caption faint">
        {current.caption} · {conceptual
          ? "conceptual architecture — presentation render, no engineering dimensions claimed"
          : "presentation render — the engineering geometry is the CadQuery/OCCT model above"}
      </div>
      <div className="gallery-rule faint">
        {renders?.presentation_rule}
      </div>
    </div>
  );
}

// R452 — the render availability notice (extracted from DossierSections
// so the deterministic battery can compile and exercise it directly).
//
// The typed render status is ALWAYS surfaced: a skipped, suppressed, or
// never-attempted visual stage is honest absence — never a silent gap,
// never re-labeled as an engineering failure ("rendering failed"), and
// never inflated into success ("visualization complete").
//
// R452 (external audit B2/B3/C7), the three measured defects fixed here:
//   B2 — every branch asserted "Engineering geometry available" while
//        production measured is_conceptual=true in 7/7 runs: the geometry
//        phrase is now DERIVED from the recorded authority
//        (engineering_authority/conceptual), never asserted (Article
//        XXVIII: a conceptual model is never promoted);
//   B3 — a null/absent status suppressed the notice entirely at the
//        call site (the "silent gap" its own comment forbids): the
//        NOT_ATTEMPTED state is an explicit branch and the call site
//        renders it;
//   C7 — the function threw on an undefined renders object ("Cannot
//        read properties of undefined"): the parameter is null-safe by
//        construction now, so a relaxed guard can never turn a notice
//        into a crash.

export interface RenderStatusInfo {
  status?: string | null;
  visual_gate?: { verdict?: string; hero_suppressed?: boolean };
}

export interface GeometryAuthorityInfo {
  engineering_authority?: string | null;
  conceptual?: boolean | null;
}

const NOT_ATTEMPTED =
  "No render was attempted on this run — no render status was " +
  "recorded. This is not a renderer failure and not a gate rejection; " +
  "the visual stage was simply not reached or not requested. ";

export function renderAvailabilityNotice(
  r: RenderStatusInfo | null | undefined,
  geometry?: GeometryAuthorityInfo | null,
): string {
  // B2: the geometry phrase follows the RECORDED authority — the audit
  // measured the old blanket claim promoting conceptual geometry to
  // engineering geometry in every branch (Article XXVIII, shipped)
  const authority = String(
    geometry?.engineering_authority ?? "",
  ).toUpperCase();
  const geometryPhrase =
    authority === "ENGINEERING" && geometry?.conceptual !== true
      ? "The recorded geometry authority on this run is the engineering " +
        "CAD model (CadQuery/OCCT)."
      : "The geometry on this run is a conceptual representation — " +
        "engineering geometry is not claimed (Article XXVIII: a " +
        "conceptual model is never promoted).";
  // C7: null-safe — an undefined renders object is a NOT_ATTEMPTED
  // notice, never a thrown TypeError
  const status = String(r?.status ?? "");
  const gate = r?.visual_gate;
  if (status === "" && gate == null) {
    // B3: the explicit NOT_ATTEMPTED branch — "no render was requested"
    // is a DIFFERENT fact from "the renderer is unavailable" (the
    // audit's Section 15 attack: the old code printed the unavailable
    // sentence with an empty parenthesis here, and silence at the call
    // site when the field was null)
    return NOT_ATTEMPTED + geometryPhrase;
  }
  if (status === "RENDER_SKIPPED_LOW_MEMORY") {
    // the typed 512 MB capacity skip — the exact state, verbatim
    return "Visual rendering was skipped at current deployment capacity " +
      "(512 MB class): the renderer did not run, which is a " +
      "deployment-capacity fact, not a geometry or gate verdict. " +
      geometryPhrase;
  }
  if (status.startsWith("RENDER_SKIPPED")) {
    return "Visual rendering was skipped — renderer infrastructure was " +
      "unavailable in this deployment. " + geometryPhrase;
  }
  if (gate?.hero_suppressed
      || (gate?.verdict != null
          && gate.verdict !== "COMPLETE_PASS"
          && gate.verdict !== "PASS")) {
    return "Presentation renders are withheld — the visual quality gate " +
      "did not certify them (fail-closed). " + geometryPhrase;
  }
  if (status !== "") {
    // an unrecognized non-empty status: typed honestly, never folded
    // into another state's sentence
    return "Visual rendering did not complete on this run (recorded " +
      "status: " + status + "). " + geometryPhrase;
  }
  return NOT_ATTEMPTED + geometryPhrase;
}

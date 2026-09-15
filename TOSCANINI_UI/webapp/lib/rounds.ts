// R464 — INVESTIGATION ROUNDS (the external audit's P0-1/P1-2).
//
// A steering action opens a NEW round of the same investigation: the
// engine records parent_session_id on the child (append-only — the
// parent record is never mutated). The audit's finding: rounds render
// as unrelated history entries, so the user believes their thread was
// lost. These pure helpers derive the ROUND STRUCTURE from the rows
// the engine already returns — nothing is invented, nothing is
// re-authored client-side (Art. X: the parentage is canonical state;
// this module only projects it).
//
// Zero dependencies, React-free — the adversarial Node suite runs
// this module directly, so the grouping contracts are executable
// evidence (Art. XVI).

export interface RoundRowInput {
  session_id: string;
  parent_session_id?: string | null;
  /** used only to keep a thread's rounds in chronological order;
   * absent dates sort first — presentation, never epistemics */
  created_at?: unknown;
}

export interface RoundRow<T extends RoundRowInput> {
  row: T;
  /** 1 for an original problem statement; N>1 for the Nth round of
   * the chain that session belongs to. */
  round: number;
  /** True when this row renders indented under a parent that is also
   * visible in the same list. */
  grouped: boolean;
}

/** The round number of one session: 1 + the number of ancestors in
 * the loaded set. Unknown ancestors (not loaded, or a chain longer
 * than the loaded rows) count as ONE step — the number stays a
 * lower bound on the true depth, never a guess beyond it. The walk
 * is bounded by the row count, so a corrupt cycle cannot spin. */
export function roundNumberOf(
  row: RoundRowInput,
  byId: Map<string, RoundRowInput>
): number {
  let depth = 0;
  let cur: RoundRowInput | undefined = row;
  const seen = new Set<string>();
  while (cur && cur.parent_session_id && !seen.has(cur.session_id)) {
    seen.add(cur.session_id);
    const parent: RoundRowInput | undefined =
      byId.get(String(cur.parent_session_id));
    if (!parent) {
      // the parent exists canonically but is not in the loaded set —
      // the chain continues beyond the viewport; count it as one step
      depth += 1;
      break;
    }
    depth += 1;
    cur = parent;
  }
  return depth + 1;
}

/** Order the visible rows so every round renders directly under its
 * parent (children indented), in chronological order within a thread,
 * while threads themselves keep the list's own recency order. A child
 * whose parent is NOT in the visible set stays in place, unindented —
 * its round number still renders, so the thread is legible even when
 * the parent is scrolled out of the capped idle view. */
export function groupRounds<T extends RoundRowInput>(
  visible: T[]
): RoundRow<T>[] {
  const byId = new Map(visible.map((r) => [r.session_id, r]));
  const childrenOf = new Map<string, T[]>();
  const orphans: T[] = [];
  for (const r of visible) {
    const pid = r.parent_session_id ? String(r.parent_session_id) : null;
    if (pid && byId.has(pid)) {
      const list = childrenOf.get(pid) ?? [];
      list.push(r);
      childrenOf.set(pid, list);
    } else {
      orphans.push(r);
    }
  }
  const out: RoundRow<T>[] = [];
  const emitted = new Set<string>();
  for (const r of orphans) {
    out.push({ row: r, round: roundNumberOf(r, byId), grouped: false });
    emitted.add(r.session_id);
    const kids = (childrenOf.get(r.session_id) ?? []).slice();
    // chronological within the thread (oldest round first)
    kids.sort((a, b) => String(a.created_at ?? "").localeCompare(String(b.created_at ?? "")));
    for (const k of kids) {
      if (emitted.has(k.session_id)) continue;
      out.push({ row: k, round: roundNumberOf(k, byId), grouped: true });
      emitted.add(k.session_id);
      // a grandchild chains onto its own parent's slot
      const grand = (childrenOf.get(k.session_id) ?? []).slice();
      grand.sort((a, b) =>
        String(a.created_at ?? "").localeCompare(String(b.created_at ?? "")));
      for (const g of grand) {
        if (emitted.has(g.session_id)) continue;
        out.push({ row: g, round: roundNumberOf(g, byId), grouped: true });
        emitted.add(g.session_id);
      }
    }
  }
  // safety: anything not emitted (defensive against shape drift) keeps
  // its original position rather than disappearing
  for (const r of visible) {
    if (!emitted.has(r.session_id)) {
      out.push({ row: r, round: roundNumberOf(r, byId), grouped: false });
    }
  }
  return out;
}

/** The newest child round of a given session, from the loaded rows —
 * the forward continuation link on a parent that has forked. Returns
 * null when the session has no child in the loaded set (honest
 * absence — the link simply does not render). */
export function latestChildOf<T extends RoundRowInput>(
  sessionId: string | null | undefined,
  rows: T[]
): T | null {
  if (!sessionId) return null;
  const kids = rows.filter(
    (r) => r.parent_session_id === sessionId
  );
  if (kids.length === 0) return null;
  kids.sort((a, b) =>
    String(b.created_at ?? "").localeCompare(String(a.created_at ?? "")));
  return kids[0] ?? null;
}

#!/usr/bin/env python3
"""R473: verify the runtime-state-hf graft — index union correctness at tip 828be9b4.
Sources: e245bbe (176) + 6a60b6f7 (34) -> tip (209). Checks: ids exact union, no
duplicates, latest-wins on overlap, chronology monotone per source order, payload trees."""
import json, subprocess, sys

REPO = "/home/z/my-project/hf_space"

def show(ref: str, path: str) -> str:
    return subprocess.run(["git", "-C", REPO, "show", f"{ref}:{path}"],
                          capture_output=True, text=True, check=True).stdout

def load_index(ref: str):
    d = json.loads(show(ref, "sessions.json"))
    s = d["sessions"] if isinstance(d, dict) and "sessions" in d else d
    return s

def ids_of(sessions):
    ids = [s.get("session_id") for s in sessions]
    dupes = {i for i in ids if ids.count(i) > 1}
    return ids, dupes

fails = []
def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(name)

old = load_index("e245bbe")          # 176
cur34 = load_index("6a60b6f7")       # 34
tip = load_index("origin/runtime-state-hf")  # 209 (graft v3)

old_ids, old_dup = ids_of(old)
cur_ids, cur_dup = ids_of(cur34)
tip_ids, tip_dup = ids_of(tip)
check("no duplicate session_id inside e245bbe index", not old_dup, str(old_dup or ""))
check("no duplicate session_id inside 34-tip index", not cur_dup, str(cur_dup or ""))
check("no duplicate session_id inside graft tip index", not tip_dup, str(tip_dup or ""))

check("e245bbe index == 176 entries", len(old) == 176, str(len(old)))
check("pre-graft tip == 34 entries", len(cur34) == 34, str(len(cur34)))
check("graft tip == 209 entries", len(tip) == 209, str(len(tip)))

old_set, cur_set, tip_set = set(old_ids), set(cur_ids), set(tip_ids)
union = old_set | cur_set
check("tip ids == exact union(176,34)", tip_set == union,
      f"missing_from_tip={sorted(union-tip_set)[:5]} invented={sorted(tip_set-union)[:5]}")
overlap = old_set & cur_set
check("overlap count consistent with 176+34-209", len(overlap) == 176 + 34 - len(tip),
      f"overlap={sorted(overlap)}")

# latest-wins on overlap: tip record must equal the NEWER of the two source records
old_by = {s["session_id"]: s for s in old}
cur_by = {s["session_id"]: s for s in cur34}
tip_by = {s["session_id"]: s for s in tip}
for sid in sorted(overlap):
    a, b = old_by.get(sid), cur_by.get(sid)
    au = (a or {}).get("updated_at") or (a or {}).get("created_at") or ""
    bu = (b or {}).get("updated_at") or (b or {}).get("created_at") or ""
    newer = a if str(au) >= str(bu) else b
    check(f"overlap id {sid}: latest-wins record matches newer source (old@{au} vs cur@{bu})",
          tip_by[sid] == newer)

# chronology: within the tip, the relative order of old-only ids preserves e245bbe order,
# and of cur-only ids preserves the 34-tip order
pos_tip = {sid: i for i, sid in enumerate(tip_ids)}
def order_preserved(source, source_ids, label):
    seq = [pos_tip[i] for i in source_ids if i in pos_tip]
    ok = seq == sorted(seq)
    check(f"chronology preserved for {label} ids ({len(seq)})", ok)
order_preserved(old, old_ids, "e245bbe")
order_preserved(cur34, cur_ids, "34-tip")

# payload trees: every non-sessions.json path at e245bbe must exist at tip with same blob
def tree_paths(ref):
    out = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", ref],
                         capture_output=True, text=True, check=True).stdout
    m = {}
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        mode, typ, sha = meta.split()
        m[path] = (typ, sha)
    return m

t_old, t_tip = tree_paths("e245bbe"), tree_paths("origin/runtime-state-hf")
payload_old = {p: s for p, s in t_old.items() if p != "sessions.json"}
missing = [p for p in payload_old if p not in t_tip]
changed = [p for p in payload_old if p in t_tip and t_tip[p] != payload_old[p] and t_tip[p][1] != payload_old[p][1]]
check("all e245bbe payload paths present at tip", not missing, f"missing={len(missing)} {missing[:5]}")
check("no e245bbe payload blob changed at tip (additive graft)", not changed, f"changed={len(changed)} {changed[:5]}")

t34 = tree_paths("6a60b6f7")
payload34 = {p: s for p, s in t34.items() if p != "sessions.json"}
missing34 = [p for p in payload34 if p not in t_tip]
check("all 34-tip payload paths present at tip", not missing34, f"missing={len(missing34)} {missing34[:5]}")

print(f"\nfiles: e245bbe={len(t_old)} tip={len(t_tip)} 34tip={len(t34)}")
print("RESULT:", "ALL GREEN" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)

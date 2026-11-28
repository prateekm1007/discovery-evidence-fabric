#!/usr/bin/env python3
"""register_trailer_violations.py — the R146 trailer-discipline
register (F36 discipline, forward-only): six twin-lane commits carry
malformed trailer blocks (Session: and Work-Id: split across
paragraphs by blank lines — the parser reads only the LAST block) or
none. CI (tests/test_article29_parallel_coordination.py) fails the
tip until each is REGISTERED in trailer_violations[] with session
attribution. Pushed history is never rewritten; the register is the
remediation."""
import json

PATH = "eval/work_claims.json"

VIOLATIONS = [
    ("c9992c04e",
     "malformed trailer block (Session:/Work-Id: split across "
     "paragraphs — the parser misses the split halves)"),
    ("1e9793a04",
     "malformed trailer block (Session:/Work-Id: split across "
     "paragraphs — the DEV-VERIFY commit names both but split by a "
     "blank line)"),
    ("ba0797606",
     "missing trailer block on a canonical-measurement-bytes commit "
     "(the v17 novelty-strength one-shot generation events + 30 rows)"),
    ("3306c30c1",
     "missing trailer block (the c-0249 verifier close)"),
    ("4019345e5",
     "missing trailer block (the DIR-4 BLOCKED-TRANSPORT typing)"),
    ("f5e21933d",
     "missing trailer block (the panel-lane hand-off typing)"),
]

NOTE = ("Attribution unambiguous: all six commits are the "
        "builder-r146s1 session's R146S1 lane (the strength lane "
        "c-0250 + the c-0249 verifier close + the panel transport "
        "typing); the commit subjects carry the lane identity and "
        "the registry additions are theirs. Registered per F36 "
        "rather than rewriting landed history (pushed history is "
        "never rewritten; remediation is forward). Detected and "
        "registered by builder-r145s1 (claim c-0253 lineage) at the "
        "DIR-7 green-tip check after the CI trailer guard named "
        "them; the commits after the window close (the R146S1 CLOSE "
        "lineage) carry well-formed trailer blocks.")


def main() -> None:
    raw = open(PATH).read()
    entries = [{
        "violation": v,
        "session_attribution": "builder-r146s1",
        "work_id_attribution": (
            "r146-v17-s2-strength / the r146s1 window-close lane "
            "(the commit's own subject + registry additions identify "
            "the lane)"),
        "registered_by": ("builder-r145s1 (the peer catch at the "
                          "DIR-7 green-tip check; claim c-0253 "
                          "lineage)"),
        "typed": NOTE,
        "sha": sha,
        "detected_at": "2026-11-24 (sandbox clock, TRUE UTC)",
    } for sha, v in VIOLATIONS]
    i = raw.find('"trailer_violations": [')
    assert i != -1
    seg = raw[i:]
    arr_close = seg.find("\n  ],")
    assert arr_close != -1
    head = raw[:i + arr_close].rstrip()
    assert head.endswith("}")
    lines = []
    for e in entries:
        lines.append("    {")
        for k, v in e.items():
            lines.append(f'      "{k}": {json.dumps(v)},')
        lines[-1] = lines[-1][:-1]
        lines.append("    },")
    new = (head + ",\n" + "\n".join(lines)[:-1] + "\n  ],"
           + raw[i + arr_close + len("\n  ],"):])
    open(PATH, "w").write(new)
    d = json.loads(new)
    tv = d["trailer_violations"]
    assert [t["sha"] for t in tv[-6:]] == [s for s, _ in VIOLATIONS]
    print("registered:", len(tv), "total; last 6:",
          [t["sha"] for t in tv[-6:]])


if __name__ == "__main__":
    main()

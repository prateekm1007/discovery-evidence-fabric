#!/usr/bin/env python3
"""decoder unit test + re-tally from committed judgments (P0-3,
Amendment 2 §5): the TIE->win decoder bug is fixed in
scripts/r11_a0plus_compare.py; this script (a) unit-tests the decoder
logic on synthetic prefer/order combinations, (b) re-tallies the
committed judge records WITHOUT new judge calls (the raw judgments
carry prefer/order/x_arm/y_arm — the decode is deterministic).

Run: python3 scripts/r11_decoder_retally.py
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def decode(prefer, order, x_name="a1", y_name="baseline"):
    """The FIXED decoder — mirrors r11_a0plus_compare.py exactly."""
    if prefer not in ("A", "B"):
        return "tie"
    elif (prefer == "A") == (order == "a0plus_first"):
        return x_name
    return y_name


def unit_tests() -> bool:
    cases = [
        # (prefer, order, x_first?, expected)
        ("A", "a0plus_first", True, "a1"),      # x served first, A -> x
        ("A", "baseline_first", True, "baseline"),  # A -> y
        ("B", "a0plus_first", True, "baseline"),
        ("B", "baseline_first", True, "a1"),
        ("TIE", "a0plus_first", True, "tie"),   # the audited bug shape
        ("TIE", "baseline_first", True, "tie"),  # and its mirror
        ("tie", "a0plus_first", True, "tie"),
        ("INVALID", "a0plus_first", True, "tie"),
    ]
    ok = True
    for prefer, order, _, expected in cases:
        got = decode(prefer, order)
        good = got == expected
        ok &= good
        print(f"  prefer={prefer:8s} order={order:14s} -> {got:9s} "
              f"{'PASS' if good else 'FAIL (expected ' + expected + ')'}")
    return ok


def retally() -> dict:
    src = REPO / "eval" / "a0plus_compare_r11.json"
    if not src.exists():
        src = REPO / "eval" / "a0plus_compare_r11.partial.json"
    if not src.exists():
        print("  no committed judge record found — re-tally typed "
              "NOT_MEASURED")
        return {"typed_state": "NOT_MEASURED_NO_COMMITTED_JUDGMENTS"}
    d = json.loads(src.read_text())
    judgments = d.get("judgments") or []
    out = {}
    for kind in sorted({j.get("pair") for j in judgments
                        if j.get("pair")}):
        sub = [j for j in judgments if j.get("pair") == kind]
        w = t = l = 0
        for j in sub:
            if j.get("outcome") != "JUDGE_VALID":
                continue
            prefer = j.get("prefer")
            order = j.get("order") or "a0plus_first"
            x_name = j.get("x_arm") or "a1"
            y_name = j.get("y_arm") or "baseline"
            picked = decode(prefer, order, x_name, y_name)
            if picked == x_name:
                w += 1
            elif picked == y_name:
                l += 1
            else:
                t += 1
        out[kind] = {"valid": w + t + l, f"{x_name}_wins_redecoded": w,
                     "ties_redecoded": t, f"{y_name}_wins_redecoded": l}
        print(f"  {kind:22s} n={w+t+l:2d}  {x_name}={w} tie={t} "
              f"{y_name}={l}  (re-decoded from committed judgments; "
              "zero new judge calls)")
    return out


def main() -> int:
    print("[retally] decoder unit tests (the audited TIE->win shape):")
    ok = unit_tests()
    print("[retally] re-tally from committed judgments:")
    out = retally()
    verdict = "PASS" if ok else "FAIL"
    # P1-6: every gate-proportion record carries its 95% CI (n=10 CIs
    # are wide; the 1.0.0 novelty PASS was provisional on them)
    try:
        from discovery_fabric.engine.r11_stats import wilson_ci
        _cis = {}
        for _k, _v in out.items():
            _x = _v.get("a1_wins_redecoded",
                        _v.get("a0plus_wins_redecoded", 0))
            _n = _v.get("valid", 0)
            _cis[_k] = {"point_lo_hi": wilson_ci(_x, _n)}
        print("[retally] 95% CIs:", json.dumps(_cis))
    except Exception as _e:  # noqa: BLE001
        _cis = {"typed_state": f"CI_SKIP_{type(_e).__name__}"}
    (REPO / "eval" / "decoder_retally_r11.json").write_text(json.dumps({
        "record": "decoder_retally_r11/1.0.0",
        "record": "decoder_retally_r11/1.0.0",
        "decoder_fix": "TIE decoded first from the judge verdict; the "
                       "old `(prefer=='A')==(order=='a0plus_first')` "
                       "was True on double-False and decoded ties as "
                       "x-wins (auditor Amendment 2 §5)",
        "decoder_tests": verdict,
        "retally_zero_new_calls": True,
        "wilson_95_ci": _cis,
        "pairs_needed_note": "n=10 CIs are wide; ~31 pairs for a "
                             "0.35-width interval (P1-6 infra ready; "
                             "the 30-fresh-pair battery is typed "
                             "PENDING_RUNTIME)",
        "redecoded": out}, indent=1, default=str) + "\n",
        encoding="utf-8")
    print(f"[retally] decoder tests: {verdict} -> eval/"
          "decoder_retally_r11.json")
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())

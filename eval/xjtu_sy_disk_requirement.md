# XJTU-SY Disk Requirement — Owner Decision One-Pager

**Work-Id:** r110-disk-requirement-doc (claim c-0147, builder-r109s2, EXECUTOR) — the R110 direction-4 item.
**At:** 2026-11-20T09:15Z (sandbox clock). **Live df at authoring time:** rootfs 9.9 GB total / 3.7 GB used / **5.7 GB free** (39% used).
**Decision requested:** pick a custody path for the full 15-bearing XJTU-SY extraction. No path below is executed without the owner decision (option B is an owner-account act).

## 1. The requirement, byte-derived (refines the ~11 GB estimate)

| Quantity | Bytes | Source (committed) |
|---|---|---|
| Archive, compressed (zip64 central directory) | 5,447,931,446 B ≈ 5.45 GB | `eval/r110_d5_zip_index.json` (peer Dir-5 tooling, 9,236 members / 15 bearings) |
| Extracted CSVs, UNCOMPRESSED — byte-verified portion (13 bearings, 7,707 members) | 10,211,571,195 B ≈ 10.21 GB | `eval/p3_realdata/xjtu_sy_listing.txt` (unrar-free per-member sizes, recomputed this window) |
| Extracted, extrapolated remainder (Bearing3_4: 1,515 members; Bearing3_5: 114 members at the verified 1.32–1.34 MB/file mean) | ≈ +2.18 GB | zip-index member counts × verified per-file mean |
| **Extracted full-set total** | **≈ 12.2 GB** (±3_4/3_5 extrapolation) | this derivation (ratio-consistent: 5.45 GB × 2.24 compression ≈ 12.2 GB) |
| RAR5 source parts (gdown, 6 volumes) | ≈ 4.2 GB | `eval/p3_realdata/xjtu_sy_parts_manifest.txt` (sha256 per part) |
| **In-place full extraction (parts + extracted + working)** | **≈ 16–17 GB** | sum |

**Disclosure (Art. 5):** the standing "~11 GB" figure (typed in `eval/r109_d7_disk_probe.json`, c-0137, verifier-recomputed c-0144) was an estimate; the byte-level derivation above says the extracted set ALONE is ≈ 12.2 GB — the in-place extraction needs ≈ 14 GB free after part-streaming, vs 5.7 GB free now. The blocker is HARDER than previously typed, not softer.

**Current coverage:** the committed 173-file two-bearing sample (Bearing3_1/3_2, R105s2; c-0138-verified) — no full life course for 13 of 15 bearings.

## 2. Options

**A. Streaming extraction, zero disk ceiling — BUILT AND EXECUTED, no owner action.** The peer's R110 Dir-5 tooling (`eval/r110_d5_zip_index.json` + `eval/r110_d5_selected_members.json`, commit 8e6cffa95): zip64 central-directory index + HTTP-range fetch of selected members, ONE member buffer peak, measure-then-discard — the uncompressed set never touches disk. **Dir-5 is DONE while this document was in flight (commit 2727b8bad): the 6-bearing subset is measured — coverage with Wilson 95% CIs per bearing committed in `eval/r110_d5_xjtu_six_bearings.json`, the 3.3 GB ceiling honored byte-for-byte.** Fetch budget 3,767,480,689 B ≈ 3.59 GiB compressed → ≈ 8.46 GB uncompressed processed in memory. Extends to all 15 bearings: ≈ 5.45 GB fetched, ≈ 12.2 GB streamed, disk peak unchanged. Cost: network + runtime only. **This is the recommended default; it covers all 3 operating conditions now.**

**B. Cloud custody of the extracted set — one owner authorization.** The restored master HF token (digest `33bc7af22c62`, live whoami-v2 this window) carries scoped `repo.write` on user `prateekm1`: the loop can create a PRIVATE dataset repo (e.g., `prateekm1/xjtu-sy-extracted`) and push the extracted CSVs there, pulling per-use. Zero sandbox disk ceiling; values stay under owner privacy control; storage consumes no inference credits. NOT executed without the owner decision (account-level act, Art. 17 custody discipline; repo carries digests-only companion records).

**C. Sandbox disk expansion.** Resume the committed 7zz-25.01 RAR5 extraction path when rootfs free ≥ 14 GB (the byte-derived resume condition supersedes the old ≥ 12 GB line). 6-part gdown source; acceptance = coverage ≥ 0.90 on ≥ 3 bearings, matched-budget table.

**D. Substitute a smaller benchmark.** FEMTO-ST/PRONOSTIA or NASA IMS subsets fit the disk today. Typed as a capability trade (cross-condition life courses lost); if it feeds any score lane it needs an auditor prereg first (Art. 12/13).

## 3. Value proposition (why the full set matters)

XJTU-SY is the only benchmark in the P3 lane with run-to-failure life courses under three operating conditions (35Hz12kN / 50Hz10kN / 50Hz25kN). Whole-life envelopes (degradation onset → failure) feed the P3 predictors' generalization axis (score lane: real-data stages); a 2-bearing sample cannot witness cross-condition degradation shapes. Option A already closes most of this gap without any owner action; option B additionally gives the set durable, re-fetchable custody beyond this sandbox (Art. 18: work that dies with the sandbox is not evidence).

**Recommendation: A now; B if durable custody of the full set is wanted; C only if the sandbox is being upgraded anyway; D as fallback only.**

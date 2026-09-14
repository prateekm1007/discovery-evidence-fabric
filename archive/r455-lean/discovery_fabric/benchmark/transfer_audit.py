"""Phase 11 — transfer-readiness audit (Coder 2).

Evaluates BUYER_RECEIVES / BUYER_MUST_DEVELOP / BUYER_MUST_VERIFY and makes
sure none collapse into TRANSFER_READY. A technology can have an excellent
dossier and still be TRANSFER_READY = FALSE — that is expected and correct.

Collapse detection (hard failures):
    TRANSFER_BOUNDARY_REMOVED   — boundary blocks absent from package
    TRANSFER_READY_COLLAPSED    — transfer_ready TRUE without reality-loop
                                  evidence (loop_verification_state != DONE)
    VV_COLLAPSED_INTO_TRANSFER  — must-verify items presented as already
                                  verified
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def audit_transfer(metrics: Dict[str, Any]) -> Dict[str, Any]:
    m = metrics
    manifest = m.get("source_manifest") or {}
    eng_spec = m.get("eng_spec")
    tb = m.get("transfer_boundary_structured") or {}
    tb_pdf = m.get("transfer_boundary_pdf") or {}

    violations: list = []
    receives = tb.get("buyer_receives") or 0
    must_create = tb.get("buyer_must_create") or 0
    pdf_elements = tb_pdf.get("elements_present") or []
    has_eng_spec = eng_spec is not None

    # generated packages carry a STRUCTURED transfer boundary — the
    # machine-readable deliverable. Stripping it is TRANSFER_BOUNDARY_REMOVED
    # even if a stale rendered PDF still shows boilerplate text: the
    # package's machine layer no longer declares what the buyer receives /
    # develops / verifies.
    if has_eng_spec and (receives == 0 or must_create == 0):
        violations.append({
            "violation": "TRANSFER_BOUNDARY_REMOVED",
            "detail": "structured transfer boundary emptied in the "
                      "machine-readable package (stale PDF text does not "
                      "restore it)"})
    if not has_eng_spec:
        # corpus-side (PDF-only) check
        if "YOU RECEIVE" not in pdf_elements and receives == 0:
            violations.append({
                "violation": "TRANSFER_BOUNDARY_REMOVED",
                "detail": "no buyer-receives block in package or spec"})
        if "YOU MUST DEVELOP" not in pdf_elements and must_create == 0:
            violations.append({
                "violation": "TRANSFER_BOUNDARY_REMOVED",
                "detail": "no buyer-must-develop block"})
    if "YOU MUST VERIFY" not in pdf_elements and has_eng_spec and \
            not (eng_spec.get("transfer_boundary") or {}).get(
                "buyer_must_verify"):
        violations.append({
            "violation": "TRANSFER_BOUNDARY_REMOVED",
            "detail": "no buyer-must-verify block — verification duty not "
                      "transferred"})

    # transfer_ready collapse: TRUE only legal with reality-loop evidence
    transfer_ready = manifest.get("transfer_ready")
    loop_state = manifest.get("loop_verification_state")
    real_loop = manifest.get("real_loop_verified")
    if transfer_ready is True:
        if loop_state not in ("DONE", "VERIFIED") or real_loop is not True:
            violations.append({
                "violation": "TRANSFER_READY_COLLAPSED",
                "detail": f"transfer_ready=TRUE with "
                          f"loop_verification_state={loop_state}, "
                          f"real_loop_verified={real_loop} — dossier depth "
                          f"must never inflate transfer readiness"})
    # must-verify presented as verified?
    vv = m.get("vv_probe") or {}
    if eng_spec and vv.get("validations_claiming_result", 0) > 0:
        violations.append({
            "violation": "VV_COLLAPSED_INTO_TRANSFER",
            "detail": "validation rows claim results — buyer-must-verify "
                      "duties presented as already performed"})

    honest_false = (transfer_ready is False) or (transfer_ready is None and
                                                 not violations)
    return {
        "buyer_receives_items": receives,
        "buyer_must_develop_items": must_create,
        "buyer_must_verify_present": "YOU MUST VERIFY" in pdf_elements,
        "transfer_ready_reported": transfer_ready,
        "loop_verification_state": loop_state,
        "real_loop_verified": real_loop,
        "transfer_ready_honest_false": bool(honest_false and not violations),
        "violations": violations,
        "verdict": "FAIL" if violations else "PASS",
        "note": "excellent dossier != transfer ready; TRANSFER_READY=FALSE "
                "is the expected honest state pre-reality (Art. XXXVIII)",
    }

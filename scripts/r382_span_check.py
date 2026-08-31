"""Check every evidence pointer/span in the R382 disposition map
against the real files (engine + live portfolio package files)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from premium_package_factory.r382.disposition import (
    DISPOSITIONS, ENGINE_ROOT, _verify_evidence_entry, folder_for)

PORTFOLIO = "/home/z/my-project/technology-transfer-portfolio-15"

ok, bad = 0, []
for num, entry in sorted(DISPOSITIONS.items()):
    pdir = os.path.join(PORTFOLIO, "DOWNLOAD", folder_for(num))
    for ev in entry.get("record_verified_basis") or []:
        errs = _verify_evidence_entry(ev, pdir, PORTFOLIO)
        if errs:
            bad.append((num, ev.get("pointer"), errs))
        else:
            ok += 1

print(f"evidence entries resolved: {ok}")
print(f"failures: {len(bad)}")
for num, ptr, errs in bad:
    print(f"  {num}: {ptr}")
    for e in errs:
        print(f"     {e}")

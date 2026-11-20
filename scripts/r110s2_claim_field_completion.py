#!/usr/bin/env python3
"""c-0147/c-0148 schema completion (the Art. 29 validator red, the
field-drift class): add the validator-required claimed_at (equal to
each claim's registered_at — the registration act IS the claiming act;
the prior session wrote the wrong field name) and artifact_paths (the
c-0147 legacy singular 'artifact' lifted into the typed list; c-0148's
target paths as registered in the claim title). Text-surgical: the
file's existing formatting is preserved."""
import json
import re
from pathlib import Path

F = Path("/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json")
text = F.read_text(encoding="utf-8")

c0148_paths = [
    "scripts/r110s2_hf_stream_upload.py",
    "scripts/r105s2_p3_stage5_xjtu.py",
    "tests/test_r105s2_p3_stage5_xjtu.py",
    "eval/xjtu_sy_hf_manifest.json",
    "eval/r110s2_hf_upload_record.json",
    "eval/r105s2_p3_stage5_xjtu_record.json",
]

blocks = [m.start() for m in re.finditer(r'"claim_id": "c-014[78]"', text)]
assert len(blocks) == 2, f"expected 2 anchors, got {len(blocks)}"


def registered_at_of(block_text):
    m = re.search(r'"registered_at": "([^"]+)"', block_text)
    assert m, "registered_at missing in block"
    return m.group(1)


new_text = text
for cid, extra in [("c-0147",
                    '   "artifact_paths": '
                    '["eval/xjtu_sy_disk_requirement.md"]\n'),
                   ("c-0148",
                    "   \"artifact_paths\": [\n"
                    + "".join(f'    "{p}",\n' for p in c0148_paths[:-1])
                    + f'    "{c0148_paths[-1]}"\n'
                    + "   ]\n")]:
    i = new_text.find(f'"claim_id": "{cid}"')
    assert i >= 0, cid
    # the end of this claim object: the registered_at line inside it
    j = new_text.find('"registered_at": "', i)
    assert 0 <= j < i + 4000, f"registered_at not after {cid}"
    line_start = new_text.rfind("\n", 0, j) + 1
    line_end = new_text.find("\n", j)
    assert line_end > 0
    indent = new_text[line_start:new_text.index('"', line_start)]
    ts = registered_at_of(new_text[i:i + 4000])
    reg_line = new_text[line_start:line_end]
    if not reg_line.rstrip().endswith(","):
        # registered_at is the block's last key — give it a comma
        new_text = (new_text[:line_start] + reg_line + ","
                    + new_text[line_end:])
        line_end += 1
    # the last inserted line needs a trailing comma IFF more keys
    # follow in the object (i.e. the next line after registered_at is
    # not the object's closing brace)
    nxt = new_text[line_end + 1:new_text.find("\n", line_end + 1)]
    end_comma = "" if nxt.lstrip().startswith("}") else ","
    ins = (f'{indent}"claimed_at": "{ts}",\n' + extra[:-1] + end_comma
           + "\n")
    new_text = new_text[:line_end + 1] + ins + new_text[line_end + 1:]

# sanity: the file still parses as JSON and the fields landed
try:
    d = json.loads(new_text)
except json.JSONDecodeError as e:
    Path("/tmp/claims_new_debug.json").write_text(new_text)
    lines = new_text.splitlines()
    ln = e.lineno
    print("DEBUG region:")
    for k in range(max(0, ln - 14), min(len(lines), ln + 3)):
        print(f"{k + 1:5d} | {lines[k]}")
    raise
for c in d["claims"]:
    if c.get("claim_id") in ("c-0147", "c-0148"):
        assert c.get("claimed_at"), cid
        assert isinstance(c.get("artifact_paths"), list)
F.write_text(new_text, encoding="utf-8")
print("c-0147 claimed_at:",
      [c["claimed_at"] for c in d["claims"]
       if c.get("claim_id") == "c-0147"][0])
print("c-0147 artifact_paths:",
      [c["artifact_paths"] for c in d["claims"]
       if c.get("claim_id") == "c-0147"][0])
print("c-0148 claimed_at:",
      [c["claimed_at"] for c in d["claims"]
       if c.get("claim_id") == "c-0148"][0])
print("c-0148 artifact_paths:", len(c0148_paths), "paths")

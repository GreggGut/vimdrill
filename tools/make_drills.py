#!/usr/bin/env python3
"""Generate drills/<id>/ from a spec file: python3 tools/make_drills.py src/week01.drills.json

Spec: a JSON list of drills. Edit drill:
  {"id": "1.1", "instructions": "...", "solution": "keys in <>-notation",
   "start": {"main.txt": "..."}, "target": {"main.txt": "..."},
   "open": ["main.txt"], "diff": true}
Task drill (config lessons):
  {"id": "10.1", "type": "task", "instructions": "...", "check": "bash script body; exit 0 = pass"}
"""
import json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for spec in json.loads(Path(sys.argv[1]).read_text()):
    d = ROOT / "drills" / spec["id"]
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    meta = {k: v for k, v in spec.items() if k not in ("start", "target", "check")}
    if spec.get("type") == "task":
        (d / "check.sh").write_text("#!/usr/bin/env bash\n" + spec["check"].rstrip() + "\n")
    else:
        meta.setdefault("open", ["main.txt"])
        for part in ("start", "target"):
            for name, text in spec[part].items():
                f = d / part / name
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(text if text.endswith("\n") else text + "\n")
    (d / "drill.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("wrote", d.relative_to(ROOT))

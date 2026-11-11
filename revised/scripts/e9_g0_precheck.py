"""E9 step 3: run the E8 G0 function on the hybrid manifest before any images are generated. Exit 1 if a condition is missing."""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("gate05b", "revision/05b_gate_with_coverage.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

manifest = json.loads(Path("revision/llm_e9/hybrid_manifest.json").read_text(encoding="utf-8"))
required = json.loads(Path("revision/policy/mission_critical_required.json").read_text(encoding="utf-8"))
cov = g.check_coverage(manifest, required)
Path("revision/llm_e9/g0_precheck.json").write_text(json.dumps(cov, ensure_ascii=False, indent=2), encoding="utf-8")
print(cov)
raise SystemExit(1 if g.missing_ids(cov) else 0)

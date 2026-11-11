"""E9 step 2: preset clean 2 + generated medium 4 and hard 4 (generation order) + preset SCN_011, SCN_012.
Generated extreme scenarios are not evaluated. 02_generate_ms_eval_dataset_seeded.py iterates the manifest as a list,
so hybrid_manifest.json stays a list and the excluded items go to hybrid_manifest_excluded.json.
If 07b fell back to preset (source preset_fallback), that source label is kept so the result is not reported as LLM output."""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from framework_utils import PRESET_SCENARIOS, normalize_scenarios  # noqa: E402

D = Path("revision/llm_e9")
run0 = json.loads((D / "manifests" / "run_00.json").read_text(encoding="utf-8"))
gen = run0[2:]
keep = [s for s in gen if s["difficulty"] in ("medium", "hard")]
excluded = [s for s in gen if s["difficulty"] == "extreme"]
if len(keep) != 8 or len(excluded) != 2:
    raise SystemExit(f"[ERROR] expected 8 kept and 2 excluded, got {len(keep)} and {len(excluded)}")

items = [{**p, "source": "preset_fixed_clean"} for p in PRESET_SCENARIOS[:2]]
items += keep
items += [{**p, "source": "expert_fixed_critical"} for p in PRESET_SCENARIOS[10:12]]
manifest = normalize_scenarios(items)
(D / "hybrid_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
(D / "hybrid_manifest_excluded.json").write_text(json.dumps({"excluded": excluded}, ensure_ascii=False, indent=2), encoding="utf-8")
for s in manifest:
    print(s["scenario_id"], s["source"], s["bucket"], s["weather"], s["time_of_day"], s["sensor_noise_level"], s["adversarial_camouflage"])
print("excluded:", [(s["scenario_id"], s["weather"], s["time_of_day"], s["sensor_noise_level"]) for s in excluded])

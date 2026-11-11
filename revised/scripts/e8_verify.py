"""E8 verification. a) and b) read the verdict files written by 05b; c) applies G0 alone to saved LLM manifests.
Output: revision/E8/verification.json"""
import importlib.util
import json
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location("gate05b", "revision/05b_gate_with_coverage.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


required = load("revision/policy/mission_critical_required.json")
out = {}

# a) preset seed 0: compare with the existing 05 run
ver = load("revision/E8/a_preset_seed0/verdict.json")
summary = load("revision/eval/preset_seed0/evaluation_summary.json")
registry = {m["model_id"]: m for m in load("revision/registry_7.json")["models"]}
old_log = Path("revision/eval/preset_seed0/cicd_log.txt").read_text(encoding="utf-8")
old_manifest = {m["model_id"] for m in load("revision/eval/preset_seed0/deploy_manifest.json")}
rows = []
for mid, verdict in ver["verdicts"].items():
    name = registry[mid]["display_name"]
    old_pass = f"{name} gate PASSED" in old_log
    old_fail = f"{name} gate FAILED" in old_log
    old = "PASS" if old_pass and not old_fail else "FAIL" if old_fail and not old_pass else "UNKNOWN"
    rows.append({"model": mid, "old_05": old, "old_in_manifest": mid in old_manifest, "new_05b": verdict,
                 "same": old == verdict.split(" ")[0] and (mid in old_manifest) == (mid in ver["deployed"])})
out["a_preset_seed0"] = {"g0_missing": ver["g0_missing"], "rows": rows, "all_same": all(r["same"] for r in rows),
                         "n_models": len(rows), "summary_models": len(summary["models"])}

# b) gemma seed 0
ver = load("revision/E8/b_gemma_seed0/verdict.json")
out["b_gemma_seed0"] = {"g0_coverage": ver["g0_coverage"], "g0_missing": ver["g0_missing"],
                        "verdicts": ver["verdicts"], "deployed": ver["deployed"]}

# c) all saved LLM manifests, G0 only
EXPECTED = {"gemma4:12b": (30, 10, 24, 4), "qwen3:4b": (10, 9, 10, 9), "qwen3.5:9b": (12, 9, 10, 7)}
DIRS = {"gemma4:12b": "revision/llm_trials_v2_gemma4_12b", "qwen3:4b": "revision/llm_trials_v2",
        "qwen3.5:9b": "revision/llm_trials_v2_qwen3.5_9b"}
out["c_manifests"] = {}
for model, d in DIRS.items():
    files = sorted(Path(d, "manifests").glob("*.json"))
    n = mc1 = mc2 = both = 0
    per_run = []
    for f in files:
        m = load(f)
        if not any(s.get("source") == "llm" for s in m):
            continue
        cov = {c["id"]: c["satisfied"] for c in g.check_coverage(m, required)}
        n += 1
        mc1 += cov["MC1"]
        mc2 += cov["MC2"]
        both += cov["MC1"] and cov["MC2"]
        per_run.append({"run": int(re.search(r"(\d+)", f.stem).group(1)), **cov})
    out["c_manifests"][model] = {"manifest_files": len(files), "with_llm_source": n, "MC1": mc1, "MC2": mc2, "both": both,
                                 "expected_n_MC1_MC2_both": EXPECTED[model],
                                 "matches_expected": (n, mc1, mc2, both) == EXPECTED[model], "per_run": per_run}

Path("revision/E8/verification.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("a) all_same =", out["a_preset_seed0"]["all_same"], "g0_missing =", out["a_preset_seed0"]["g0_missing"])
for r in out["a_preset_seed0"]["rows"]:
    print("  ", r)
print("b)", out["b_gemma_seed0"]["g0_missing"], out["b_gemma_seed0"]["verdicts"], "deployed =", out["b_gemma_seed0"]["deployed"])
for k, v in out["c_manifests"].items():
    print("c)", k, {x: v[x] for x in ("manifest_files", "with_llm_source", "MC1", "MC2", "both", "expected_n_MC1_MC2_both", "matches_expected")})

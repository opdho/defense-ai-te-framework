"""E9 step 1 check: is the new generation identical to run 0 of the existing 30-run gemma4:12b trial? Comparison only; never fails the run."""
import json
from pathlib import Path


def attempts(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


old = [a for a in attempts("revision/llm_trials_v2_gemma4_12b/attempts.jsonl") if a["run"] == 0]
new = attempts("revision/llm_e9/attempts.jsonl")
old_m = json.loads(Path("revision/llm_trials_v2_gemma4_12b/manifests/run_00.json").read_text(encoding="utf-8"))
new_m = json.loads(Path("revision/llm_e9/manifests/run_00.json").read_text(encoding="utf-8"))
res = {"old_attempts": len(old), "new_attempts": len(new), "new_pass_attempt": next((a["attempt"] for a in new if a["pass"]), None),
       "seeds_old": [a["seed"] for a in old], "seeds_new": [a["seed"] for a in new],
       "raw_identical_attempt1": old[0]["raw"] == new[0]["raw"], "manifest_identical": old_m == new_m,
       "fields_differing": [
           {"scenario_id": a.get("scenario_id"), "field": k, "old": a.get(k), "new": b.get(k)}
           for a, b in zip(old_m, new_m) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]}
Path("revision/llm_e9/compare_with_run0.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print({k: v for k, v in res.items() if k != "fields_differing"}, "n_fields_differing =", len(res["fields_differing"]))

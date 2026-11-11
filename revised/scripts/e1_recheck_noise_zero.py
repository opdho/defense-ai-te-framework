"""
E1 supplementary re-check: recompute validator results from the saved raw LLM outputs with one fix.

07_llm_scenario_trials.py check_item() uses `float(s.get("sensor_noise_level", 1) or 1) > 0.10`
for the clean-reference rule, so a noise value of exactly 0.0 becomes 1 and an otherwise clean
"easy" item is flagged as semantic:dirty_clean_reference. This script re-runs the same checks on
trials_raw.jsonl with only that expression corrected (missing -> 1, 0.0 stays 0.0). No LLM calls.

Usage (from D:\\park\\test5):
  python revision\\scripts\\e1_recheck_noise_zero.py --trials revision\\llm_trials --out revision\\llm_trials\\recheck_noise_zero.json
"""

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path


def load_trials_module():
    path = Path(__file__).resolve().parents[1] / "07_llm_scenario_trials.py"
    spec = importlib.util.spec_from_file_location("trials07", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--trials", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--num", type=int, default=12)
    a = p.parse_args()

    m = load_trials_module()
    orig_check = m.check_item

    def fixed_check(s):
        v = [x for x in orig_check(s) if x != "semantic:dirty_clean_reference"]
        if isinstance(s, dict) and s.get("difficulty") == "easy":
            noise = s.get("sensor_noise_level", 1)
            noise = 1.0 if noise is None else float(noise)
            if s.get("weather") != "clear" or s.get("time_of_day") != "day" or s.get("adversarial_camouflage") \
                    or noise > 0.10:
                v.append("semantic:dirty_clean_reference")
        return v

    res = {}
    rows = [json.loads(l) for l in open(Path(a.trials) / "trials_raw.jsonl", encoding="utf-8")]
    for setting in sorted({r["setting"] for r in rows}):
        stats = {}
        for name, chk in (("original_rule", orig_check), ("fixed_rule", fixed_check)):
            ivr, usable, n_json, viol = [], 0, 0, Counter()
            for r in (x for x in rows if x["setting"] == setting):
                try:
                    items = m.parse(r["raw"])
                except Exception:
                    continue
                n_json += 1
                iv = [chk(s) for s in items]
                ivr.append(sum(1 for v in iv if v) / max(1, len(items)))
                viol.update(x.split(":")[0] if ":" in x else x for v in iv for x in v)
                usable += int(not any(iv) and not m.check_run(items, a.num))
            stats[name] = {"json_parsed_runs": n_json,
                           "mean_item_violation_rate": round(sum(ivr) / len(ivr), 4) if ivr else None,
                           "usable_runs": usable, "violation_counts": dict(viol)}
        res[setting] = stats
    Path(a.out).write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

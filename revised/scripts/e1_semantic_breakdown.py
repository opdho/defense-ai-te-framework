"""
E1 v1: break down the L1+L2 semantic:dirty_clean_reference violations by which non-clean condition
was mixed into an "easy" item (weather != clear, time_of_day != day, camouflage, noise > 0.10).
The violation set is taken with the same expression as 07 check_item (so the total matches summary.json);
items flagged only because of the noise == 0.0 bug are reported separately.

Usage (from D:\\park\\test5):
  python revision\\scripts\\e1_semantic_breakdown.py --raw revision\\llm_trials\\trials_raw.jsonl --out revision\\llm_trials\\semantic_breakdown.json
"""

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    combos, single, examples, total, bug_only = Counter(), Counter(), [], 0, 0
    for line in open(a.raw, encoding="utf-8"):
        r = json.loads(line)
        if r["setting"] != "L1+L2":
            continue
        for idx, s in enumerate(json.loads(r["raw"]), 1):
            if s.get("difficulty") != "easy":
                continue
            noise_v1 = float(s.get("sensor_noise_level", 1) or 1)  # same expression as 07 (0.0 -> 1)
            flagged = s.get("weather") != "clear" or s.get("time_of_day") != "day" \
                or s.get("adversarial_camouflage") or noise_v1 > 0.10
            if not flagged:
                continue
            total += 1
            causes = []
            if s.get("weather") != "clear":
                causes.append(f"weather={s.get('weather')}")
            if s.get("time_of_day") != "day":
                causes.append(f"time={s.get('time_of_day')}")
            if s.get("adversarial_camouflage"):
                causes.append("camouflage")
            if float(s.get("sensor_noise_level") or 0) > 0.10:
                causes.append("noise>0.10")
            if not causes:
                causes = ["noise==0.0 (validator bug)"]
                bug_only += 1
            combos[" + ".join(causes)] += 1
            single.update(c.split("=")[0] if "=" in c else c for c in causes)
            examples.append({"run": r["run"], "item": idx, "causes": causes, "scenario": s})

    out = {"total_flagged_easy_items": total, "flagged_only_by_noise_zero_bug": bug_only,
           "by_combination": dict(combos.most_common()), "by_condition_any": dict(single.most_common()),
           "examples": examples}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "examples"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

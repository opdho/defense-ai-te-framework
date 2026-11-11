"""
07b_llm_scenario_trials_v2.py  (revision E1 v2; 07_llm_scenario_trials.py is left unchanged)

Changes from v1:
  - The two clean references are fixed by the framework (preset SCN_001, SCN_002 prepended);
    the LLM generates only 10 scenarios: medium 4, hard 4, extreme 2.
  - The same semantic rules are written into the system prompt and the validator:
      medium : no camouflage, noise <= 0.30, at least 1 degradation factor
               (non-clear weather or dusk/night)
      hard   : 0.30 <= noise <= 0.50, at least 2 degradation factors
               (non-clear weather, dusk/night, camouflage)
      extreme: noise >= 0.50, night, non-clear weather and camouflage all present
    The v1 enum / range / type / required / forbidden-term checks are reused unchanged from 07.
  - On validation failure the scenarios are regenerated up to 3 more times (new seed each time,
    same prompt); if all 4 attempts fail the preset set is used (fallback).
    Every attempt and its violations are logged.

Usage (from D:\\park\\test5):
  python revision\\07b_llm_scenario_trials_v2.py check-preset --out revision\\llm_trials_v2_presetcheck.json
  python revision\\07b_llm_scenario_trials_v2.py scenarios --model qwen3:4b --runs 30 --outdir revision\\llm_trials_v2

Outputs (scenarios): attempts.jsonl (every attempt: raw output, parse status, violations),
                     trial_metrics.csv (one row per run), summary.json,
                     manifests\\run_XX.json (final 12-scenario manifest of each run, llm or preset),
                     best_manifest_llm_v2.json (first run whose LLM output passed validation)
"""
import argparse
import csv
import importlib.util
import json
import re
import time
from collections import Counter
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent


def _load_v1():
    spec = importlib.util.spec_from_file_location("trials07", HERE / "07_llm_scenario_trials.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


v1 = _load_v1()  # also puts framework_utils on sys.path
from framework_utils import PRESET_SCENARIOS  # noqa: E402

ENUMS, REQUIRED, FORBIDDEN, FAMILY, BUCKET, SEVERITY = v1.ENUMS, v1.REQUIRED, v1.FORBIDDEN, v1.FAMILY, v1.BUCKET, v1.SEVERITY
N_LLM = 10
TARGET_MIX = {"medium": 4, "hard": 4, "extreme": 2}
MAX_RETRIES = 3

SYSTEM_PROMPT = """You are a defense AI T&E scenario planner.
Output JSON array only. No markdown, no prose, no code block.
Each scenario must contain:
weather(clear|foggy|rainy|snowy|hazy),
time_of_day(day|dusk|night),
target_density(low|medium|high),
sensor_noise_level(0.0~1.0),
adversarial_camouflage(boolean),
visibility_km(0.1~10.0),
difficulty(easy|medium|hard|extreme),
description(string).
Clean reference scenarios are added by the framework. Do not generate easy scenarios.
Generate exactly 10 scenarios: 4 medium, 4 hard, 2 extreme.
A degradation factor is one of: weather other than clear, time_of_day dusk or night, adversarial_camouflage true.
Rules for each difficulty:
medium: adversarial_camouflage false, sensor_noise_level <= 0.30, at least 1 degradation factor from weather other than clear or time_of_day dusk/night.
hard: sensor_noise_level between 0.30 and 0.50, at least 2 degradation factors (camouflage counts).
extreme: sensor_noise_level >= 0.50, time_of_day night, weather other than clear, adversarial_camouflage true.
Avoid GPS jamming and any class list in the output.
"""

USER_PROMPT = ("Generate 10 scenario records (4 medium, 4 hard, 2 extreme) for automated scenario-based "
               "object detection T&E. The output is for corruption robustness and deployment gate evaluation.")


def call_llm(host, model, fmt, seed, temperature):
    body = {"model": model, "stream": False, "think": False,
            "options": {"seed": seed, "temperature": temperature},
            "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                         {"role": "user", "content": USER_PROMPT}],
            "format": fmt}
    t0 = time.time()
    r = requests.post(f"{host}/api/chat", json=body, timeout=300)
    r.raise_for_status()
    return r.json()["message"]["content"].strip(), time.time() - t0


def _num(s, key):
    """Numeric field or None (missing / wrong type is already reported by the v1 checks)."""
    try:
        return float(s.get(key))
    except (TypeError, ValueError):
        return None


def degradation_factors(s, with_camo):
    f = int(s.get("weather") != "clear") + int(s.get("time_of_day") in ("dusk", "night"))
    if with_camo:
        f += int(s.get("adversarial_camouflage") is True)
    return f


def semantic_violations(s):
    v, d, noise = [], s.get("difficulty"), _num(s, "sensor_noise_level")
    if d == "easy":  # used only when checking the preset clean references
        if s.get("weather") != "clear" or s.get("time_of_day") != "day" or s.get("adversarial_camouflage") \
                or noise is None or noise > 0.10:
            v.append("semantic:easy_not_clean")
    elif d == "medium":
        if s.get("adversarial_camouflage"):
            v.append("semantic:medium_camo")
        if noise is None or noise > 0.30:
            v.append("semantic:medium_noise_gt_0.30")
        if degradation_factors(s, with_camo=False) < 1:
            v.append("semantic:medium_no_degradation")
    elif d == "hard":
        if noise is None or not 0.30 <= noise <= 0.50:
            v.append("semantic:hard_noise_not_0.30_0.50")
        if degradation_factors(s, with_camo=True) < 2:
            v.append("semantic:hard_lt2_factors")
    elif d == "extreme":
        if noise is None or noise < 0.50:
            v.append("semantic:extreme_noise_lt_0.50")
        if s.get("time_of_day") != "night":
            v.append("semantic:extreme_not_night")
        if s.get("weather") == "clear":
            v.append("semantic:extreme_clear_weather")
        if s.get("adversarial_camouflage") is not True:
            v.append("semantic:extreme_no_camo")
    return v


def check_item(s):
    """v1 checks except its easy-clean rule (replaced by the per-difficulty rules above)."""
    v = [x for x in v1.check_item(s) if x != "semantic:dirty_clean_reference"]
    if isinstance(s, dict):
        v += semantic_violations(s)
    return v


def check_run(items):
    v = []
    if len(items) != N_LLM:
        v.append("run:count")
    mix = Counter(s.get("difficulty") for s in items if isinstance(s, dict))
    if any(mix.get(k, 0) != n for k, n in TARGET_MIX.items()) or sum(mix.values()) != sum(TARGET_MIX.values()):
        v.append("run:difficulty_mix")
    return v


def to_manifest(items):
    """preset SCN_001, SCN_002 + the 10 LLM scenarios as SCN_003..SCN_012."""
    out = [{**p, "source": "preset_fixed_clean"} for p in PRESET_SCENARIOS[:2]]
    for i, s in enumerate(items, 3):
        b = BUCKET[s["difficulty"]]
        parts = []
        if s["weather"] != "clear":
            parts.append(FAMILY[s["weather"]])
        if s["time_of_day"] in ("dusk", "night"):
            parts.append(s["time_of_day"])
        if float(s["sensor_noise_level"]) >= 0.30:
            parts.append("noise")
        if s["adversarial_camouflage"]:
            parts.append("camo")
        out.append({**s, "scenario_id": f"SCN_{i:03d}", "bucket": b, "severity": SEVERITY[b],
                    "corruption_family": "+".join(parts) if parts else "none",
                    "safety_critical": b == "critical", "source": "llm"})
    return out


def run_check_preset(a):
    res = []
    for s in PRESET_SCENARIOS[:12]:
        v = check_item(s)
        res.append({"scenario_id": s["scenario_id"], "difficulty": s["difficulty"], "violations": v})
        print(f"{s['scenario_id']} {s['difficulty']:<8} {'PASS' if not v else 'FAIL ' + '|'.join(v)}")
    run_v = check_run(PRESET_SCENARIOS[2:12])
    print(f"run-level (SCN_003..012): {'PASS' if not run_v else 'FAIL ' + '|'.join(run_v)}")
    out = {"items": res, "run_level_SCN003_012": run_v,
           "all_pass": not run_v and all(not r["violations"] for r in res)}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"all_pass={out['all_pass']} -> {a.out}")


def run_scenarios(a):
    outdir = Path(a.outdir)
    if outdir.exists() and any(outdir.iterdir()):
        raise FileExistsError(f"output directory is not empty: {outdir}")
    (outdir / "manifests").mkdir(parents=True, exist_ok=True)
    fmt = v1.schema(with_enum=True)
    rows, best = [], None
    att_log = open(outdir / "attempts.jsonl", "w", encoding="utf-8")
    for run in range(a.runs):
        rec = {"run": run, "passed_attempt": None, "attempts": 0, "final_source": "preset_fallback",
               "total_latency_s": 0.0, "attempt_violations": []}
        final_items = None
        for attempt in range(1, MAX_RETRIES + 2):
            seed = a.seed0 + run * 10 + attempt
            arec = {"run": run, "attempt": attempt, "seed": seed, "api_ok": 0, "json_ok": 0, "n_items": 0,
                    "item_violations": [], "run_violations": [], "pass": 0, "latency_s": None, "raw": None}
            try:
                raw, dt = call_llm(a.host, a.model, fmt, seed, a.temperature)
                arec.update(api_ok=1, latency_s=round(dt, 2), raw=raw)
                rec["total_latency_s"] += dt
                items = v1.parse(raw)
                arec.update(json_ok=1, n_items=len(items))
                arec["item_violations"] = [check_item(s) for s in items]
                arec["run_violations"] = check_run(items)
                arec["pass"] = int(not any(arec["item_violations"]) and not arec["run_violations"])
            except Exception as e:  # noqa: BLE001 - every failure is a measured outcome
                arec["run_violations"] = [f"exception:{type(e).__name__}"]
            att_log.write(json.dumps(arec, ensure_ascii=False) + "\n")
            att_log.flush()
            flat = sorted({x for v in arec["item_violations"] for x in v} | set(arec["run_violations"]))
            rec["attempt_violations"].append("|".join(flat) if flat else "")
            rec["attempts"] = attempt
            print(f"run {run:02d} attempt {attempt} seed={seed} api={arec['api_ok']} json={arec['json_ok']} "
                  f"pass={arec['pass']} {'|'.join(flat)}", flush=True)
            if arec["pass"]:
                rec.update(passed_attempt=attempt, final_source="llm")
                final_items = items
                break
        manifest = to_manifest(final_items) if final_items else \
            [{**p, "source": "preset_fallback"} for p in PRESET_SCENARIOS[:12]]
        (outdir / "manifests" / f"run_{run:02d}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if final_items and best is None:
            best = manifest
            rec["is_best"] = 1
        rec["total_latency_s"] = round(rec["total_latency_s"], 2)
        rec["attempt_violations"] = " || ".join(rec["attempt_violations"])
        rows.append(rec)
    att_log.close()

    fields = ["run", "passed_attempt", "attempts", "final_source", "total_latency_s", "attempt_violations", "is_best"]
    with open(outdir / "trial_metrics.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in fields} for r in rows)

    attempts = [json.loads(l) for l in open(outdir / "attempts.jsonl", encoding="utf-8")]
    n = len(rows)
    item_counts = Counter(x for at in attempts for v in at["item_violations"] for x in v)
    run_counts = Counter(x for at in attempts for x in at["run_violations"])
    summary = {
        "model": a.model, "runs": n, "llm_scenarios_per_run": N_LLM, "target_mix": TARGET_MIX,
        "max_retries": MAX_RETRIES, "temperature": a.temperature, "seed_rule": "seed0 + run*10 + attempt",
        "first_attempt_pass_rate": round(sum(r["passed_attempt"] == 1 for r in rows) / n, 4),
        "cumulative_pass_rate_by_attempt": {
            str(k): round(sum(r["passed_attempt"] is not None and r["passed_attempt"] <= k for r in rows) / n, 4)
            for k in range(1, MAX_RETRIES + 2)},
        "final_fallback_rate": round(sum(r["final_source"] == "preset_fallback" for r in rows) / n, 4),
        "mean_attempts_per_run": round(sum(r["attempts"] for r in rows) / n, 4),
        "mean_generation_time_per_run_s": round(sum(r["total_latency_s"] for r in rows) / n, 2),
        "mean_latency_per_attempt_s": round(sum(at["latency_s"] or 0 for at in attempts) / len(attempts), 2),
        "n_attempts": len(attempts),
        "attempt_api_success_rate": round(sum(at["api_ok"] for at in attempts) / len(attempts), 4),
        "attempt_json_parse_rate": round(sum(at["json_ok"] for at in attempts) / len(attempts), 4),
        "item_violation_counts_all_attempts": dict(item_counts.most_common()),
        "run_violation_counts_all_attempts": dict(run_counts.most_common()),
        "best_manifest_run": next((r["run"] for r in rows if r.get("is_best")), None),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if best:
        (outdir / "best_manifest_llm_v2.json").write_text(json.dumps(best, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] first passing manifest (run {summary['best_manifest_run']}) -> {outdir / 'best_manifest_llm_v2.json'}")
    else:
        print("[WARN] no run passed validation; best_manifest_llm_v2.json not written")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check-preset")
    c.add_argument("--out", required=True)
    s = sub.add_parser("scenarios")
    s.add_argument("--host", default="http://localhost:11434")
    s.add_argument("--model", default="qwen3:4b")
    s.add_argument("--runs", type=int, default=30)
    s.add_argument("--seed0", type=int, default=2000)
    s.add_argument("--temperature", type=float, default=0.7)
    s.add_argument("--outdir", required=True)
    a = p.parse_args()
    run_check_preset(a) if a.cmd == "check-preset" else run_scenarios(a)


if __name__ == "__main__":
    main()

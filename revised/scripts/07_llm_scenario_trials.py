"""
07_llm_scenario_trials.py  (revision experiment for reviewer 2-1 / reviewer 3-1)

Runs the LLM scenario generator N times under three guardrail settings and
reports how often the output is usable, so the paper can show what the LLM
actually produced instead of only describing the mechanism.

  L1      : system prompt only (no JSON schema passed to the API)
  L1+L2   : system prompt + JSON schema with enum / required constraints
  L1+L2+L3: L1+L2 output passed through a rule validator; any run that fails
            validation is replaced by the preset set (fallback)

Usage (run inside the framework folder that has framework_utils.py):
  python 07_llm_scenario_trials.py scenarios --model qwen3:4b --runs 30 --num 12 --outdir llm_trials
  python 07_llm_scenario_trials.py report-check --summary framework_eval/evaluation_summary.json \
         --reports framework_reports_llm

Outputs (scenarios): llm_trials/trials_raw.jsonl, llm_trials/trial_metrics.csv,
                     llm_trials/summary.json, llm_trials/best_manifest_llm.json
"""
import argparse
import csv
import json
import re
import time
from collections import Counter
from pathlib import Path

import requests

import sys as _sys
from pathlib import Path as _P
for _p in (_P(__file__).resolve().parent, _P(__file__).resolve().parent.parent):
    if (_p / 'framework_utils.py').exists():
        _sys.path.insert(0, str(_p))
        break

from framework_utils import PRESET_SCENARIOS

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
Generate a balanced mix across easy / medium / hard / extreme.
The first two scenarios should be clean reference scenarios.
Avoid GPS jamming and any class list in the output.
"""

ENUMS = {
    "weather": ["clear", "foggy", "rainy", "snowy", "hazy"],
    "time_of_day": ["day", "dusk", "night"],
    "target_density": ["low", "medium", "high"],
    "difficulty": ["easy", "medium", "hard", "extreme"],
}
REQUIRED = ["weather", "time_of_day", "target_density", "sensor_noise_level",
            "adversarial_camouflage", "visibility_km", "difficulty", "description"]
FORBIDDEN = [r"\bgps\b", r"jamm", r"cyber", r"military_tank", r"military_truck",
             r"military_vehicle", r"\bsoldier\b", r"class list"]
FAMILY = {"foggy": "fog", "rainy": "rain", "snowy": "snow", "hazy": "haze"}
BUCKET = {"easy": "clean_reference", "medium": "operational", "hard": "adverse", "extreme": "critical"}
SEVERITY = {"clean_reference": 0, "operational": 1, "adverse": 2, "critical": 3}


def schema(with_enum: bool):
    props = {
        "weather": {"type": "string"},
        "time_of_day": {"type": "string"},
        "target_density": {"type": "string"},
        "sensor_noise_level": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "adversarial_camouflage": {"type": "boolean"},
        "visibility_km": {"type": "number", "minimum": 0.1, "maximum": 10.0},
        "difficulty": {"type": "string"},
        "description": {"type": "string"},
    }
    if with_enum:
        for k, v in ENUMS.items():
            props[k]["enum"] = v
    return {"type": "array", "items": {"type": "object", "properties": props, "required": REQUIRED}}


def call_llm(host, model, num, fmt, seed, temperature):
    user = (f"Generate {num} scenario records for automated scenario-based object detection T&E. "
            "The output is for corruption robustness and deployment gate evaluation.")
    body = {"model": model, "stream": False, "think": False,
            "options": {"seed": seed, "temperature": temperature},
            "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                         {"role": "user", "content": user}]}
    if fmt is not None:
        body["format"] = fmt
    t0 = time.time()
    r = requests.post(f"{host}/api/chat", json=body, timeout=300)
    r.raise_for_status()
    return r.json()["message"]["content"].strip(), time.time() - t0


def parse(raw):
    txt = re.sub(r"^```[a-zA-Z0-9_\-]*\n?", "", raw)
    txt = re.sub(r"\n?```$", "", txt)
    data = json.loads(txt)
    if isinstance(data, dict):  # some models wrap the array
        data = next((v for v in data.values() if isinstance(v, list)), [data])
    return data


def check_item(s):
    """Return list of violation codes for one scenario dict."""
    v = []
    if not isinstance(s, dict):
        return ["not_object"]
    for k in REQUIRED:
        if k not in s:
            v.append(f"missing:{k}")
    for k, allowed in ENUMS.items():
        if k in s and s[k] not in allowed:
            v.append(f"enum:{k}")
    try:
        if not 0.0 <= float(s.get("sensor_noise_level", -1)) <= 1.0:
            v.append("range:noise")
    except (TypeError, ValueError):
        v.append("type:noise")
    try:
        if not 0.1 <= float(s.get("visibility_km", -1)) <= 10.0:
            v.append("range:visibility")
    except (TypeError, ValueError):
        v.append("type:visibility")
    if "adversarial_camouflage" in s and not isinstance(s["adversarial_camouflage"], bool):
        v.append("type:camo")
    text = json.dumps(s, ensure_ascii=False).lower()
    if any(re.search(p, text) for p in FORBIDDEN):
        v.append("forbidden_term")
    # semantic rule: a clean reference must actually be clean, otherwise clean_map50 is contaminated
    if s.get("difficulty") == "easy":
        if s.get("weather") != "clear" or s.get("time_of_day") != "day" or s.get("adversarial_camouflage") \
                or float(s.get("sensor_noise_level", 1) or 1) > 0.10:
            v.append("semantic:dirty_clean_reference")
    return v


def check_run(items, num):
    """Run-level rules on top of the item checks."""
    v = []
    if len(items) != num:
        v.append("count")
    diffs = [s.get("difficulty") for s in items if isinstance(s, dict)]
    if not all(d in diffs for d in ENUMS["difficulty"]):
        v.append("unbalanced_difficulty")
    if len(items) >= 2 and not all(isinstance(s, dict) and s.get("difficulty") == "easy" for s in items[:2]):
        v.append("first_two_not_clean")
    return v


def to_manifest(items):
    out = []
    for i, s in enumerate(items, 1):
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


def run_scenarios(a):
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    settings = {"L1": None, "L1+L2": schema(with_enum=True)}
    rows, raw_log, best = [], open(outdir / "trials_raw.jsonl", "w", encoding="utf-8"), None
    for setting, fmt in settings.items():
        for run in range(a.runs):
            seed = a.seed0 + run
            rec = {"setting": setting, "run": run, "seed": seed, "api_ok": 0, "json_ok": 0,
                   "n_items": 0, "item_violation_rate": None, "run_violations": "", "usable": 0,
                   "latency_s": None, "violations": ""}
            try:
                raw, dt = call_llm(a.host, a.model, a.num, fmt, seed, a.temperature)
                rec["api_ok"], rec["latency_s"] = 1, round(dt, 2)
                raw_log.write(json.dumps({"setting": setting, "run": run, "raw": raw}, ensure_ascii=False) + "\n")
                items = parse(raw)
                rec["json_ok"], rec["n_items"] = 1, len(items)
                item_v = [check_item(s) for s in items]
                bad = [v for v in item_v if v]
                rec["item_violation_rate"] = round(len(bad) / max(1, len(items)), 4)
                flat = Counter(x.split(":")[0] if ":" in x else x for v in item_v for x in v)
                rec["violations"] = json.dumps(dict(flat))
                run_v = check_run(items, a.num)
                rec["run_violations"] = "|".join(run_v)
                rec["usable"] = int(not bad and not run_v)
                if rec["usable"] and setting == "L1+L2" and best is None:
                    best = to_manifest(items)
            except Exception as e:  # noqa: BLE001 - every failure is a measured outcome
                rec["run_violations"] = f"exception:{type(e).__name__}"
            rows.append(rec)
            print(f"[{setting}] run {run:02d} api={rec['api_ok']} json={rec['json_ok']} "
                  f"usable={rec['usable']} {rec['run_violations']}")
    raw_log.close()

    with open(outdir / "trial_metrics.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {"model": a.model, "runs_per_setting": a.runs, "num_scenarios": a.num, "settings": {}}
    for setting in settings:
        rs = [r for r in rows if r["setting"] == setting]
        n = len(rs)
        ivr = [r["item_violation_rate"] for r in rs if r["item_violation_rate"] is not None]
        summary["settings"][setting] = {
            "api_success_rate": round(sum(r["api_ok"] for r in rs) / n, 4),
            "json_parse_rate": round(sum(r["json_ok"] for r in rs) / n, 4),
            "mean_item_violation_rate": round(sum(ivr) / len(ivr), 4) if ivr else None,
            "usable_run_rate": round(sum(r["usable"] for r in rs) / n, 4),
            "violation_counts": dict(sum((Counter(json.loads(r["violations"])) for r in rs if r["violations"]), Counter())),
            "run_violation_counts": dict(Counter(x for r in rs for x in r["run_violations"].split("|") if x)),
        }
    l2 = [r for r in rows if r["setting"] == "L1+L2"]
    summary["settings"]["L1+L2+L3"] = {
        "final_valid_rate": 1.0,
        "fallback_rate": round(1 - sum(r["usable"] for r in l2) / len(l2), 4),
        "note": "runs failing validation are replaced by the preset set, so every run ends with a valid manifest",
    }
    (outdir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if best:
        (outdir / "best_manifest_llm.json").write_text(json.dumps(best, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] first usable L1+L2 manifest -> {outdir/'best_manifest_llm.json'}")
    else:
        fb = PRESET_SCENARIOS[: a.num]
        (outdir / "best_manifest_llm.json").write_text(json.dumps(fb, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[WARN] no usable LLM manifest; preset written as fallback")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def run_report_check(a):
    """Count numbers in each LLM report that do not match any value in evaluation_summary.json."""
    summary = json.loads(Path(a.summary).read_text(encoding="utf-8"))
    for model_id, d in summary["models"].items():
        truth = set()
        for k, v in d.items():
            if isinstance(v, (int, float)):
                truth.add(round(float(v), 4))
        for c in d.get("criteria", {}).values():
            truth.update({round(float(c["value"]), 4), round(float(c["threshold"]), 4)})
        rpt = Path(a.reports) / f"report_{model_id}.txt"
        if not rpt.exists():
            print(f"[SKIP] {rpt} missing")
            continue
        text = rpt.read_text(encoding="utf-8")
        nums = [float(x) for x in re.findall(r"(?<![\w.])\d+\.\d+", text)]
        unmatched = [x for x in nums if all(abs(x - t) > 5e-4 for t in truth)]
        print(f"{model_id}: decimals in report={len(nums)}, not traceable to summary={len(unmatched)} {unmatched[:10]}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scenarios")
    s.add_argument("--host", default="http://localhost:11434")
    s.add_argument("--model", default="qwen3:4b")
    s.add_argument("--runs", type=int, default=30)
    s.add_argument("--num", type=int, default=12)
    s.add_argument("--seed0", type=int, default=1000)
    s.add_argument("--temperature", type=float, default=0.7)
    s.add_argument("--outdir", default="llm_trials")
    r = sub.add_parser("report-check")
    r.add_argument("--summary", required=True)
    r.add_argument("--reports", required=True)
    a = p.parse_args()
    run_scenarios(a) if a.cmd == "scenarios" else run_report_check(a)


if __name__ == "__main__":
    main()

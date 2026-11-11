"""
05b_gate_with_coverage.py  (revision E8; 05_simulate_cicd_gate.py is left unchanged)

G0: every required mission-critical condition must match at least one scenario in the required bucket.
  - G0 not met: every model is "INCOMPLETE (G0: <missing ids>)" and the deployment manifest is [].
    G1-G4 values are logged for reference only.
  - G0 met: G1-G4 are handled by run_pipeline imported from 05_simulate_cicd_gate.py.
Build, security and deployment lines in the log come from 05 and are simulated, not executed.

Usage (from the project folder):
  python revision\\05b_gate_with_coverage.py --registry ... --summary ... --scenarios <meta json>
      --required revision\\policy\\mission_critical_required.json --out-log ... --out-manifest ...
"""
import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_05():
    spec = importlib.util.spec_from_file_location("gate05", ROOT / "05_simulate_cicd_gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gate05 = _load_05()
from framework_utils import dump_json, load_json  # noqa: E402


def matches(scn, cond):
    try:
        noise = float(scn.get("sensor_noise_level"))
    except (TypeError, ValueError):
        return False
    return (scn.get("weather") == cond["weather"]
            and scn.get("time_of_day") == cond["time_of_day"]
            and scn.get("adversarial_camouflage") is cond["adversarial_camouflage"]
            and noise >= cond["sensor_noise_level_min"])


def check_coverage(scenarios, required):
    """One record per required condition; only scenarios in the required bucket can satisfy it."""
    pool = [s for s in scenarios if s.get("bucket") == required["required_bucket"]]
    res = []
    for cond in required["conditions"]:
        hit = [s.get("scenario_id") for s in pool if matches(s, cond)]
        res.append({"id": cond["id"], "satisfied": bool(hit), "matched_scenarios": hit})
    return res


def missing_ids(coverage):
    return [c["id"] for c in coverage if not c["satisfied"]]


def failed_criteria(decision):
    return [cid for cid, c in decision.get("criteria", {}).items() if not c.get("pass")]


def main():
    p = argparse.ArgumentParser(description="CI/CD gate with mission-critical scenario coverage check (G0).")
    p.add_argument("--registry", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--scenarios", required=True)
    p.add_argument("--required", required=True)
    p.add_argument("--out-log", required=True)
    p.add_argument("--out-manifest", required=True)
    p.add_argument("--out-verdict", help="optional JSON with G0 result and per-model verdicts")
    a = p.parse_args()

    registry = load_json(Path(a.registry))
    summary = load_json(Path(a.summary))
    model_map = {m["model_id"]: m for m in registry.get("models", [])}
    coverage = check_coverage(load_json(Path(a.scenarios)), load_json(Path(a.required)))
    missing = missing_ids(coverage)

    logs = ["NOTE build, security and deployment lines are simulated by 05_simulate_cicd_gate.py, not executed"]
    for c in coverage:
        level = "OK" if c["satisfied"] else "FAIL"
        logs.append(gate05.log(f"G0 {c['id']}: {'satisfied by ' + ','.join(c['matched_scenarios']) if c['satisfied'] else 'MISSING'}",
                               level, gate05.C.G if c["satisfied"] else gate05.C.R))

    manifests, verdicts = [], {}
    for model_id, decision in summary.get("models", {}).items():
        if missing:
            verdict = f"INCOMPLETE (G0: {', '.join(missing)})"
            logs.append(gate05.log(f"{model_id} {verdict}: deployment blocked", "FAIL", gate05.C.R))
            for cid, crit in decision.get("criteria", {}).items():
                logs.append(gate05.log(f"reference only {cid}: {crit['metric']} {crit['operator']} {crit['threshold']} "
                                       f"(observed={crit['value']}, pass={crit.get('pass')})", "INFO"))
        else:
            result = gate05.run_pipeline(model_id, model_map.get(model_id, {}), decision, logs)
            if result:
                manifests.append(result)
                verdict = "PASS"
            else:
                verdict = f"FAIL ({', '.join(failed_criteria(decision))})"
        verdicts[model_id] = verdict
        logs.append(f"VERDICT {model_id}: {verdict}")
        print(f"VERDICT {model_id}: {verdict}")

    Path(a.out_log).write_text("\n".join(logs), encoding="utf-8")
    dump_json(manifests, Path(a.out_manifest))
    if a.out_verdict:
        dump_json({"g0_coverage": coverage, "g0_missing": missing, "verdicts": verdicts,
                   "deployed": [m["model_id"] for m in manifests]}, Path(a.out_verdict))
    print(f"[OK] {a.out_log} / {a.out_manifest} written")


if __name__ == "__main__":
    main()

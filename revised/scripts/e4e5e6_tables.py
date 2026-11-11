"""
Build the E4 / E5 / E6 tables from result files only (no inference).

  E4 : A vs A_rep and B vs B_rep per-scenario map50 diff (submission eval set),
       T3 final (A_rep, B_rep, C_clean, D) and factor effects (architecture s-n, recipe robust-base).
  E5 : T4, 7 models x seeds 0-4: mean +- std (sample std, ddof=1) of each metric, per-seed gate verdicts,
       verdict agreement (count of the most frequent verdict / number of seeds), SCN_011 map50 mean +- std.
  E6 : T5, critical floor 0.05-0.30 (step 0.05): critical_failure_count and verdict per model, recomputed
       from the per-scenario CSVs (G1-G3 values taken from the same CSV, G4 recomputed with the new floor).

Usage (from D:\\park\\test5):
  python revision\\scripts\\e4e5e6_tables.py --out-md revision\\E4E5E6_tables.md --out-json revision\\E4E5E6_tables.json
"""

import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

SUB = Path("revision/eval/2x2_submitted_set")      # A, B (submission weights), C, D on the submission images
RET = Path("revision/eval/2x2_retrain")            # A_rep, C_clean, B_rep on the same images
ORIG = Path("_original_submission/framework_eval")  # submission run (A, B)
SEEDS = [Path(f"revision/eval/preset_seed{k}") for k in range(5)]
MODELS7 = ["model_A", "model_B", "model_C", "model_D", "model_A_rep", "model_B_rep", "model_C_clean"]
METRICS = ["clean_map50", "mpc50", "rpc50", "adverse_map50", "worstcase_map50", "critical_failure_count"]
GATES = [("g1", "clean_map50", ">=", 0.7), ("g2", "adverse_map50", ">=", 0.5), ("g3", "rpc50", ">=", 0.65)]
FLOORS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]


def rows(d: Path, mid: str):
    with open(d / f"eval_results_{mid}.csv", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def summ(d: Path, mid: str):
    return json.loads((d / "evaluation_summary.json").read_text(encoding="utf-8"))["models"][mid]


def map50(rs, sid):
    return float(next(r for r in rs if r["scenario_id"] == sid)["map50"])


def failed(m):
    f = [k.split("_")[0].upper() for k, c in m["criteria"].items() if not c["pass"]]
    return m["overall_judgment"] + (f" ({', '.join(f)})" if f else "")


def csv_metrics(rs):
    mean = lambda v: sum(v) / len(v)
    clean = mean([float(r["map50"]) for r in rs if r["bucket"] == "clean_reference"])
    mpc = mean([float(r["map50"]) for r in rs if r["bucket"] != "clean_reference"])
    return {"clean_map50": clean, "mpc50": mpc, "rpc50": mpc / clean,
            "adverse_map50": mean([float(r["map50"]) for r in rs if r["bucket"] in ("adverse", "critical")]),
            "critical": [float(r["map50"]) for r in rs if r["bucket"] == "critical"]}


def judge_at_floor(rs, floor):
    m = csv_metrics(rs)
    ok = all((m[k] >= t) for _, k, _, t in GATES)
    cfc = sum(1 for v in m["critical"] if v < floor)
    return cfc, "PASS" if ok and cfc <= 0 else "FAIL"


def f4(x):
    return f"{x:.4f}"


def ms(v):
    return f"{statistics.mean(v):.4f} ± {statistics.stdev(v):.4f}" if len(v) > 1 else f4(v[0])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out-md", required=True)
    p.add_argument("--out-json", required=True)
    a = p.parse_args()
    md, js = [], {}

    # ---------------- E4 ----------------
    if (RET / "evaluation_summary.json").is_file():
        md.append("## E4. 재학습 모델 (투고본 평가셋)\n")
        pairs = [("model_A", SUB, "model_A_rep"), ("model_B", SUB, "model_B_rep"), ("model_C", SUB, "model_C_clean")]
        js["E4_diff"] = {}
        for base, bd, rep in pairs:
            rb, rr = rows(bd, base), rows(RET, rep)
            md.append(f"### {base} vs {rep} (map50, Δ = {rep} − {base})\n")
            md.append(f"| SCN | bucket | {base} | {rep} | Δ |\n|---|---|---|---|---|")
            d = []
            for r in rb:
                v1, v2 = float(r["map50"]), map50(rr, r["scenario_id"])
                d.append({"scenario_id": r["scenario_id"], "base": v1, "rep": v2, "delta": v2 - v1})
                md.append(f"| {r['scenario_id']} | {r['bucket']} | {f4(v1)} | {f4(v2)} | {v2 - v1:+.4f} |")
            sb, sr = summ(bd, base), summ(RET, rep)
            md.append("")
            md.append(f"| 지표 | {base} | {rep} | Δ |\n|---|---|---|---|")
            for k in METRICS:
                md.append(f"| {k} | {sb[k]} | {sr[k]} | {sr[k] - sb[k]:+.4f} |")
            md.append(f"| 판정 | {failed(sb)} | {failed(sr)} | |")
            md.append(f"\nmax |Δ map50| = {max(abs(x['delta']) for x in d):.4f}\n")
            js["E4_diff"][f"{base}_vs_{rep}"] = {"per_scenario": d, "summary_base": {k: sb[k] for k in METRICS},
                                                 "summary_rep": {k: sr[k] for k in METRICS},
                                                 "verdict_base": failed(sb), "verdict_rep": failed(sr)}

        t3 = {"model_A_rep": (RET, "n·base"), "model_B_rep": (RET, "s·robust"),
              "model_C_clean": (RET, "n·robust"), "model_D": (SUB, "s·base")}
        md.append("### T3 최종 (투고본 평가셋, 열화 1회분)\n")
        md.append("| 모델 | 구성 | clean_map50 | mPC50 | rPC50 | adverse_map50 | SCN_011 map50 | critical_failure_count | 판정 |\n|---|---|---|---|---|---|---|---|---|")
        T3 = {}
        for mid, (d, cfg) in t3.items():
            s = summ(d, mid)
            T3[mid] = {k: s[k] for k in METRICS} | {"scn011_map50": map50(rows(d, mid), "SCN_011"), "verdict": failed(s)}
            md.append(f"| {mid} | {cfg} | {s['clean_map50']:.4f} | {s['mpc50']:.4f} | {s['rpc50']:.4f} | {s['adverse_map50']:.4f} | "
                      f"{T3[mid]['scn011_map50']:.4f} | {s['critical_failure_count']} | {failed(s)} |")
        keys = ["clean_map50", "mpc50", "rpc50", "adverse_map50", "scn011_map50", "critical_failure_count"]
        eff = {"arch (s−n), base": ("model_D", "model_A_rep"), "arch (s−n), robust": ("model_B_rep", "model_C_clean"),
               "recipe (robust−base), n": ("model_C_clean", "model_A_rep"), "recipe (robust−base), s": ("model_B_rep", "model_D")}
        md.append("\n### 요인 효과 (차이)\n")
        md.append("| 효과 | 계산 | " + " | ".join(keys) + " |\n|---|---|" + "---|" * len(keys))
        js["T3"], js["T3_effects"] = T3, {}
        for name, (x, y) in eff.items():
            v = {k: T3[x][k] - T3[y][k] for k in keys}
            js["T3_effects"][name] = v
            md.append(f"| {name} | {x} − {y} | " + " | ".join(f"{v[k]:+.4f}" for k in keys) + " |")
        md.append("")
    else:
        md.append("## E4: revision/eval/2x2_retrain 없음 (미실행)\n")

    # ---------------- E5 ----------------
    avail = [d for d in SEEDS if (d / "evaluation_summary.json").is_file()]
    md.append(f"## E5. T4 — 열화 시드 반복 (시드 {len(avail)}개: {', '.join(d.name for d in avail)}; std는 표본 표준편차)\n")
    if avail:
        T4 = {}
        md.append("| 모델 | " + " | ".join(METRICS) + " | SCN_011 map50 | 시드별 판정 | 판정 일치율 |\n|---|" + "---|" * (len(METRICS) + 3))
        for mid in MODELS7:
            have = [d for d in avail if mid in json.loads((d / "evaluation_summary.json").read_text(encoding="utf-8"))["models"]]
            if not have:
                continue
            ss = [summ(d, mid) for d in have]
            scn = [map50(rows(d, mid), "SCN_011") for d in have]
            ver = [s["overall_judgment"] for s in ss]
            top = Counter(ver).most_common(1)[0]
            T4[mid] = {"seeds": [d.name for d in have],
                       **{k: [s[k] for s in ss] for k in METRICS}, "scn011_map50": scn,
                       "verdicts": [failed(s) for s in ss], "agreement": f"{top[1]}/{len(ver)} {top[0]}"}
            md.append(f"| {mid} | " + " | ".join(ms([s[k] for s in ss]) for k in METRICS) +
                      f" | {ms(scn)} | {'; '.join(failed(s) for s in ss)} | {top[1]}/{len(ver)} {top[0]} |")
        js["T4"] = T4
        md.append("\n투고본 값(시드 없음, `_original_submission/framework_eval`):\n")
        md.append("| 모델 | " + " | ".join(METRICS) + " | SCN_011 map50 | 판정 |\n|---|" + "---|" * (len(METRICS) + 2))
        for mid in ["model_A", "model_B"]:
            s = summ(ORIG, mid)
            md.append(f"| {mid} | " + " | ".join(str(s[k]) for k in METRICS) + f" | {map50(rows(ORIG, mid), 'SCN_011'):.4f} | {failed(s)} |")
        md.append("")

    # ---------------- E6 ----------------
    md.append("## E6. T5 — critical floor 민감도 (평가 CSV로 재계산)\n")
    src = {"model_A": SUB, "model_B": SUB, "model_C": SUB, "model_D": SUB,
           "model_A_rep": RET, "model_B_rep": RET, "model_C_clean": RET}
    md.append("### 투고본 평가셋 (critical_failure_count / 판정)\n")
    md.append("| 모델 | " + " | ".join(f"{f:.2f}" for f in FLOORS) + " |\n|---|" + "---|" * len(FLOORS))
    T5 = {}
    for mid, d in src.items():
        if not (d / f"eval_results_{mid}.csv").is_file():
            continue
        rs = rows(d, mid)
        T5[mid] = {f"{f:.2f}": judge_at_floor(rs, f) for f in FLOORS}
        md.append(f"| {mid} | " + " | ".join(f"{c} / {v}" for c, v in T5[mid].values()) + " |")
    js["T5_submission_set"] = T5
    if avail:
        md.append(f"\n### 시드 {len(avail)}개 (PASS 시드 수 / 시드 수; 괄호는 critical_failure_count 시드별)\n")
        md.append("| 모델 | " + " | ".join(f"{f:.2f}" for f in FLOORS) + " |\n|---|" + "---|" * len(FLOORS))
        T5s = {}
        for mid in MODELS7:
            have = [d for d in avail if (d / f"eval_results_{mid}.csv").is_file()]
            if not have:
                continue
            T5s[mid] = {}
            cells = []
            for f in FLOORS:
                r = [judge_at_floor(rows(d, mid), f) for d in have]
                T5s[mid][f"{f:.2f}"] = r
                cells.append(f"{sum(v == 'PASS' for _, v in r)}/{len(r)} ({','.join(str(c) for c, _ in r)})")
            md.append(f"| {mid} | " + " | ".join(cells) + " |")
        js["T5_seeds"] = T5s
    md.append("")

    # check: recomputed verdict at floor 0.20 must equal the stored verdict
    mism = []
    for mid, d in src.items():
        if (d / f"eval_results_{mid}.csv").is_file():
            if judge_at_floor(rows(d, mid), 0.20)[1] != summ(d, mid)["overall_judgment"]:
                mism.append(mid)
    md.append(f"검증: floor 0.20 재계산 판정과 evaluation_summary 판정 불일치 = {mism if mism else '없음'}\n")
    js["check_floor020_mismatch"] = mism

    Path(a.out_md).write_text("\n".join(md), encoding="utf-8")
    Path(a.out_json).write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()

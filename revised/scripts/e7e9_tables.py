"""Tables for E7 (LLM-only scenario set) and E9 (recommended configuration), read only from result files. Output: revision/E7E9_tables.md and stdout."""
import csv
import json
from pathlib import Path

ORDER = ["model_A", "model_B", "model_D", "model_A_rep", "model_B_rep", "model_C_clean"]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def rows(d, m):
    with open(Path(d) / f"eval_results_{m}.csv", encoding="utf-8-sig", newline="") as f:
        return {r["scenario_id"]: r for r in csv.DictReader(f)}


def verdict(dec):
    fails = [c.split("_")[0].upper() for c, v in dec["criteria"].items() if not v["pass"]]
    return "PASS" if not fails else "FAIL (" + ",".join(fails) + ")"


def tables(title, src):
    head = "| 모델 | clean_map50 | mPC50 | rPC50 | adverse_map50 | SCN_011 | SCN_012 | worstcase_map50 | critical_failure_count | 판정 |"
    out = [f"#### {title} 지표", "", head, "|---|---|---|---|---|---|---|---|---|---|"]
    scn = [f"#### {title} 시나리오별 map50", "", "| 시나리오 | " + " | ".join(m.replace("model_", "") for m in ORDER) + " |",
           "|---|" + "---|" * len(ORDER)]
    per = {}
    for m in ORDER:
        d = src[m]
        dec = load(Path(d) / "evaluation_summary.json")["models"][m]
        r = per[m] = rows(d, m)
        out.append(f"| {m} | {dec['clean_map50']:.4f} | {dec['mpc50']:.4f} | {dec['rpc50']:.4f} | {dec['adverse_map50']:.4f} | "
                   f"{float(r['SCN_011']['map50']):.4f} | {float(r['SCN_012']['map50']):.4f} | {dec['worstcase_map50']:.4f} | "
                   f"{dec['critical_failure_count']} | {verdict(dec)} |")
    for s in sorted(per[ORDER[0]]):
        scn.append(f"| {s} | " + " | ".join(f"{float(per[m][s]['map50']):.4f}" for m in ORDER) + " |")
    return out + [""] + scn + [""]


OLD, E7, E9 = "revision/eval/llm_gemma4_12b_seed0", "revision/eval/e7_gemma_seed0_retrain", "revision/eval/e9_hybrid_seed0"
md = ["### E7", ""] + tables("표 E7", {**{m: OLD for m in ORDER[:3]}, **{m: E7 for m in ORDER[3:]}})
md += ["### E9", ""] + tables("표 E9", {m: E9 for m in ORDER})

md += ["#### hybrid 매니페스트 시나리오 조건", "", "| ID | source | bucket | weather | time_of_day | density | noise | camo | vis_km |", "|---|---|---|---|---|---|---|---|---|"]
for s in load("revision/meta/e9_hybrid_seed0.json"):
    md.append(f"| {s['scenario_id']} | {s['source']} | {s['bucket']} | {s['weather']} | {s['time_of_day']} | {s['target_density']} | "
              f"{s['sensor_noise_level']} | {s['adversarial_camouflage']} | {s['visibility_km']} |")
md += ["", "제외된 LLM extreme: " + "; ".join(f"{s['weather']}+{s['time_of_day']} noise {s['sensor_noise_level']}"
                                         for s in load("revision/llm_e9/hybrid_manifest_excluded.json")["excluded"]), ""]

md += ["#### 같은 시드에서 E9 고정 시나리오와 preset 시드 0 비교 (map50, E9 − preset_seed0)", "",
       "| 모델 | SCN_001 | SCN_002 | SCN_011 | SCN_012 |", "|---|---|---|---|---|"]
for m in ORDER:
    a, b = rows(E9, m), rows("revision/eval/preset_seed0", m)
    md.append(f"| {m} | " + " | ".join(f"{float(a[s]['map50']) - float(b[s]['map50']):+.4f}" for s in ("SCN_001", "SCN_002", "SCN_011", "SCN_012")) + " |")

text = "\n".join(md) + "\n"
Path("revision/E7E9_tables.md").write_text(text, encoding="utf-8")
print(text)

"""Check that Figures 2 and 3 of the submitted manuscript were drawn from the submitted per-scenario CSVs.

The submitted Figures 2, 3 and 4 are submitted/figures/fig_scenario_lines.*, fig_bucket_mAP50.* and
fig_policy_summary.*, written by submitted/scripts/06_visualize_summary.py from
submitted/results/framework_eval/eval_results_model_{A,B}.csv.
This script reads the plotted coordinates from the vector PDFs, converts them to mAP50 using the y-axis
tick marks, and compares them with the CSV values.

Usage (from the repository root):  pip install pdfplumber && python submitted/verify_submitted_figures.py
"""
import csv
import statistics as st
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figures"
CSV = ROOT / "results" / "framework_eval"
TICKS = ["0.0", "0.2", "0.4", "0.6", "0.8", "1.0"]


def load(model):
    with open(CSV / f"eval_results_model_{model}.csv", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def y_axis(page):
    """Return a function mapping a PDF y (top-based) to a data value, using the tick marks next to the tick labels."""
    marks = sorted({round(l["top"], 3) for l in page.lines if abs(l["x1"] - l["x0"]) < 6})
    labels = {w["text"]: (w["top"] + w["bottom"]) / 2 for w in page.extract_words() if w["text"] in TICKS}
    pos = {t: min(marks, key=lambda m: abs(m - labels[t])) for t in TICKS}
    y0, y1 = pos["0.0"], pos["1.0"]
    return lambda y: (y0 - y) / (y0 - y1)


def check_lines():
    page = pdfplumber.open(FIG / "fig_scenario_lines.pdf").pages[0]
    to_val = y_axis(page)
    series = [c for c in page.curves if len(c["pts"]) == 12]
    out = []
    for model, curve in zip("AB", series):
        rows = load(model)
        for (x, y), r in zip(curve["pts"], rows):
            out.append((model, r["scenario_id"], float(r["map50"]), to_val(y)))
    return out


def check_bars():
    page = pdfplumber.open(FIG / "fig_bucket_mAP50.pdf").pages[0]
    to_val = y_axis(page)
    bars = sorted([r for r in page.rects if r["height"] > 3 and 20 < r["width"] < 80 and r["non_stroking_color"] not in (1.0, (1.0,), [1.0])],
                  key=lambda r: r["x0"])
    buckets = ["clean_reference", "operational", "adverse", "critical"]
    out = []
    for i, b in enumerate(buckets):
        for j, model in enumerate("AB"):
            rows = load(model)
            mean = st.mean(float(r["map50"]) for r in rows if r["bucket"] == b)
            scn = ", ".join(r["scenario_id"][-3:] for r in rows if r["bucket"] == b)
            bar = bars[2 * i + j]
            out.append((model, f"{b} ({scn})", mean, to_val(bar["top"])))
    return out


def main():
    lines = ["# Submitted Figure 2 (scenario-wise mAP50): plotted value vs CSV", "",
             "| Model | Scenario | CSV map50 | Plotted | Abs. diff |", "|---|---|---|---|---|"]
    rows = check_lines()
    lines += [f"| {m} | {s} | {c:.4f} | {p:.4f} | {abs(c - p):.4f} |" for m, s, c, p in rows]
    lines += ["", f"Max abs. diff: {max(abs(c - p) for *_, c, p in rows):.5f}", "",
              "# Submitted Figure 3 (bucket mean mAP50): bar height vs CSV bucket mean", "",
              "| Model | Bucket (scenarios) | CSV mean | Bar height | Abs. diff |", "|---|---|---|---|---|"]
    bars = check_bars()
    lines += [f"| {m} | {b} | {c:.4f} | {p:.4f} | {abs(c - p):.4f} |" for m, b, c, p in bars]
    lines += ["", f"Max abs. diff: {max(abs(c - p) for *_, c, p in bars):.5f}", "",
              "Note: the adverse bucket bar averages SCN_007-010 only; the policy metric adverse_map50 averages SCN_007-012."]
    text = "\n".join(lines)
    print(text)
    (ROOT / "VERIFY_SUBMITTED_FIGURES.md").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

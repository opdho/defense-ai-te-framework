"""
08_revision_figures.py

Draws the scenario, bucket and policy figures directly from the per-scenario
evaluation CSVs so every plotted value can be traced to the raw numbers,
with value labels, gate reference lines and neutral candidate names.

  python 08_revision_figures.py --csv-a framework_eval/eval_results_model_A.csv \
         --csv-b framework_eval/eval_results_model_B.csv --outdir revision_figures
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3de"
SERIES = [  # validated categorical slots 1-2; marker/linestyle/hatch give a second, print-safe encoding
    {"color": "#2a78d6", "marker": "o", "ls": "-", "hatch": None},
    {"color": "#eb6834", "marker": "s", "ls": "--", "hatch": "//"},
]
GATES = {"clean_map50": 0.70, "adverse_map50": 0.50, "rPC50": 0.65}
CRITICAL_FLOOR = 0.20

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False,
})


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def mean(rows, pred):
    v = [float(r["map50"]) for r in rows if pred(r)]
    return sum(v) / len(v)


def metrics(rows):
    clean = mean(rows, lambda r: r["bucket"] == "clean_reference")
    mpc = mean(rows, lambda r: r["bucket"] != "clean_reference")
    return {"clean_map50": clean,
            "adverse_map50": mean(rows, lambda r: r["bucket"] in ("adverse", "critical")),
            "rPC50": mpc / clean}


def save(fig, outdir, stem):
    for ext in ("png", "pdf"):
        fig.savefig(outdir / f"{stem}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {outdir/stem}.png/.pdf")


def fig2(models, outdir):
    ids = [r["scenario_id"] for r in models[0][1]]
    x = np.arange(len(ids))
    fig, ax = plt.subplots(figsize=(10, 4.4))
    for b0, b1, name in [(-0.5, 1.5, "clean_reference"), (1.5, 5.5, "operational"),
                         (5.5, 9.5, "adverse"), (9.5, 11.5, "critical")]:
        ax.axvspan(b0, b1, color="#f3f2ee" if name in ("operational", "critical") else "white", lw=0, zorder=0)
        ax.text((b0 + b1) / 2, 1.0, name, ha="center", va="bottom", fontsize=8, color=MUTED)
    ax.axhline(CRITICAL_FLOOR, color=INK, lw=1, ls=":", zorder=1)
    ax.text(-0.4, CRITICAL_FLOOR + 0.012, "critical floor 0.20", ha="left", va="bottom",
            fontsize=8, color=INK)
    for k, (name, rows) in enumerate(models):
        st = SERIES[k]
        y = [float(r["map50"]) for r in rows]
        ax.plot(x, y, color=st["color"], ls=st["ls"], lw=2, marker=st["marker"], ms=6,
                markeredgecolor="white", markeredgewidth=1.2, label=name, zorder=3)
        for i in range(6, len(ids)):  # label only the adverse/critical region
            dx, dy, ha = (0, 9, "center") if k == 1 else (0, -14, "center")
            custom = {("SCN_011", 1): (-9, -4, "right"), ("SCN_011", 0): (9, 2, "left"),
                      ("SCN_012", 0): (9, -4, "left"), ("SCN_007", 1): (-9, 2, "right")}
            dx, dy, ha = custom.get((ids[i], k), (dx, dy, ha))
            ax.annotate(f"{y[i]:.3f}", (x[i], y[i]), textcoords="offset points", xytext=(dx, dy),
                        ha=ha, va="center", fontsize=7.5, color=INK, zorder=4,
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.9))
    ax.set_xticks(x)
    ax.set_xticklabels(ids, rotation=30, ha="right")
    ax.set_xlim(-0.5, len(ids) - 0.5)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("mAP50")
    ax.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, 1.06))
    save(fig, outdir, "fig2_scenario_mAP50_rev")


def fig3(models, outdir):
    buckets = ["clean_reference", "operational", "adverse", "critical"]
    x = np.arange(len(buckets))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for k, (name, rows) in enumerate(models):
        st = SERIES[k]
        vals = [mean(rows, lambda r, b=b: r["bucket"] == b) for b in buckets]
        pos = x + (k - 0.5) * (w + 0.02)
        ax.bar(pos, vals, w, color=st["color"], hatch=st["hatch"], edgecolor="white", lw=0, label=name)
        for p, v in zip(pos, vals):
            ax.text(p, v + 0.015, f"{v:.3f}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{b}\n({n})" for b, n in zip(buckets, ["SCN_001-002", "SCN_003-006",
                                                                 "SCN_007-010", "SCN_011-012"])])
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Mean mAP50 per bucket")
    ax.legend(loc="upper right")
    save(fig, outdir, "fig3_bucket_mAP50_rev")


def fig4(models, outdir):
    names = list(GATES)
    x = np.arange(len(names))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for k, (name, rows) in enumerate(models):
        st = SERIES[k]
        m = metrics(rows)
        vals = [m[n] for n in names]
        pos = x + (k - 0.5) * (w + 0.02)
        ax.bar(pos, vals, w, color=st["color"], hatch=st["hatch"], edgecolor="white", lw=0, label=name)
        for p, v, n in zip(pos, vals, names):
            verdict = "PASS" if v >= GATES[n] else "FAIL"
            ax.text(p, v + 0.015, f"{v:.3f}\n{verdict}", ha="center", va="bottom", fontsize=7.5, color=INK,
                    zorder=4, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.9))
    for i, n in enumerate(names):
        ax.hlines(GATES[n], i - 0.42, i + 0.42, colors=INK, linestyles=":", lw=1.2)
        ax.text(i + 0.43, GATES[n], f"gate {GATES[n]:.2f}", va="center", fontsize=7.5, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(["G1 clean_map50\n(SCN_001-002)", "G2 adverse_map50\n(SCN_007-012)",
                        "G3 rPC50\n(mPC50 / clean_map50)"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Metric value")
    ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.12))
    save(fig, outdir, "fig4_policy_metrics_rev")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv-a", required=True)
    p.add_argument("--csv-b", required=True)
    p.add_argument("--name-a", default="Candidate A (YOLO11n, base recipe)")
    p.add_argument("--name-b", default="Candidate B (YOLO11s, robust recipe)")
    p.add_argument("--outdir", default="revision_figures")
    a = p.parse_args()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    models = [(a.name_a, load(a.csv_a)), (a.name_b, load(a.csv_b))]
    fig2(models, out)
    fig3(models, out)
    fig4(models, out)


if __name__ == "__main__":
    main()

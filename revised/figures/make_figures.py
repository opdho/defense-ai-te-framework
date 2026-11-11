# Draws Figures 2-4 of the revised paper from tables.json (run make_tables.py first).
import json, statistics as st
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
H = Path(__file__).parent
T = json.load(open(H / "tables.json"))
OUT = H / "output"
OUT.mkdir(exist_ok=True)
NEW = {"A": "A'", "B": "B'", "C": "C", "D": "D"}
LAB = {"A": "A (YOLO11n, base)", "B": "B (YOLO11s, robust)", "C": "C (YOLO11n, robust)", "D": "D (YOLO11s, base)"}
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3de"
SER = {"A": dict(color="#2a78d6", marker="o", ls="-", hatch=None), "B": dict(color="#eb6834", marker="s", ls="--", hatch="//"),
       "C": dict(color="#1baf7a", marker="^", ls="-.", hatch="\\\\"), "D": dict(color="#eda100", marker="D", ls=":", hatch="..")}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False})
S = T["scn"]; B = T["bucket"]; SC = list(S["A"].keys())
def save(fig, stem):
    for e in ("png", "pdf"): fig.savefig(OUT / f"{stem}.{e}", dpi=300, bbox_inches="tight")
    plt.close(fig)

# Figure 2: scenario-wise mAP50, A and B, labels on SCN_007-012
fig, ax = plt.subplots(figsize=(8.6, 4.2))
x = np.arange(len(SC))
spans = [("clean_reference", 0, 1), ("operational", 2, 5), ("adverse", 6, 9), ("critical", 10, 11)]
for i, (nm, a, b) in enumerate(spans):
    if i % 2: ax.axvspan(a - .5, b + .5, color="#f2f1ed", zorder=0)
    ax.text((a + b) / 2, 1.0, nm, ha="center", va="bottom", color=MUTED, fontsize=8)
for k in "AB":
    y = [S[NEW[k]][s] for s in SC]; sp = SER[k]
    ax.plot(x, y, color=sp["color"], ls=sp["ls"], lw=2, marker=sp["marker"], ms=6, mec="white", mew=1.2, label=LAB[k], zorder=3)
    for i in range(6, 12):
        off = {("A", 10): (20, 2), ("B", 10): (-24, 6), ("A", 11): (20, -2), ("A", 9): (0, -14)}.get((k, i), (0, 10 if k == "B" else -14))
        ax.annotate(f"{y[i]:.3f}", (x[i], y[i]), textcoords="offset points", xytext=off, ha="center", fontsize=7.5, color=INK,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=.85), zorder=4)
ax.axhline(0.20, color=INK, ls=(0, (1, 2)), lw=1); ax.text(-0.4, 0.215, "critical floor 0.20", fontsize=8, color=INK)
ax.set_xticks(x); ax.set_xticklabels(SC, rotation=30, ha="right"); ax.set_ylim(0, 1.05); ax.set_xlim(-.5, 11.5); ax.set_ylabel("mAP50")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=2)
save(fig, "fig2_scenario_mAP50")

# Figure 3: bucket mean mAP50, four models
fig, ax = plt.subplots(figsize=(8.6, 4.0))
bk = [("clean_reference", "clean_reference\n(SCN_001-002)"), ("operational", "operational\n(SCN_003-006)"), ("adverse", "adverse\n(SCN_007-010)"), ("critical", "critical\n(SCN_011-012)")]
w = 0.2
for j, k in enumerate("ABCD"):
    vals = [st.mean(S[NEW[k]][s] for s in SC if B[s] == b) for b, _ in bk]; sp = SER[k]
    xs = np.arange(4) + (j - 1.5) * w
    ax.bar(xs, vals, w * 0.92, color=sp["color"], hatch=sp["hatch"], edgecolor="white", lw=0, label=LAB[k])
    for xx, v in zip(xs, vals): ax.text(xx, v + 0.012, f"{v:.3f}", ha="center", va="bottom", fontsize=6.8, color=INK, rotation=90)
ax.set_xticks(range(4)); ax.set_xticklabels([l for _, l in bk]); ax.set_ylim(0, 1.0); ax.set_ylabel("Mean mAP50 per bucket")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.15), ncol=4, fontsize=8)
save(fig, "fig3_bucket_mAP50")

# Figure 4: policy metrics with gate lines, four models
M = T["met"]; gates = [("clean", "G1 clean_map50\n(SCN_001-002)", 0.70), ("adv", "G2 adverse_map50\n(SCN_007-012)", 0.50), ("rpc", "G3 rPC50\n(mPC50 / clean_map50)", 0.65)]
fig, ax = plt.subplots(figsize=(8.6, 4.2))
for j, k in enumerate("ABCD"):
    sp = SER[k]; xs = np.arange(3) + (j - 1.5) * w
    vals = [M[NEW[k]][g] for g, _, _ in gates]
    ax.bar(xs, vals, w * 0.92, color=sp["color"], hatch=sp["hatch"], edgecolor="white", lw=0, label=LAB[k])
    for xx, v, (_, _, t) in zip(xs, vals, gates):
        ax.text(xx, (v if v >= t or t - v > 0.16 else t) + 0.015, f"{v:.3f} {'PASS' if v >= t else 'FAIL'}", ha="center", va="bottom", fontsize=6.6, color=INK, rotation=90, zorder=5, bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none"))
for i, (_, _, t) in enumerate(gates):
    ax.plot([i - 0.47, i + 0.47], [t, t], color=INK, ls=(0, (1, 1.5)), lw=1.2, zorder=4)
    ax.text(i + 0.49, t, f"gate {t:.2f}", va="center", fontsize=7.5, color=INK)
ax.set_xticks(range(3)); ax.set_xticklabels([l for _, l, _ in gates]); ax.set_ylim(0, 1.12); ax.set_ylabel("Metric value"); ax.set_xlim(-0.6, 2.85)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=4, fontsize=8)
save(fig, "fig4_policy_metrics")
print("ok")

import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from framework_utils import load_csv_rows, load_json, safe_float


def save(fig, outdir: Path, stem: str):
    fig.tight_layout()
    for ext in ('png', 'pdf'):
        fig.savefig(outdir / f'{stem}.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'[OK] {stem}.png/.pdf')


def load_rows(summary):
    rows = {}
    for model_id, dec in summary.get('models', {}).items():
        rows[model_id] = load_csv_rows(Path(dec['results_csv']))
    return rows


def fig_policy_summary(summary, outdir):
    model_ids = list(summary.get('models', {}).keys())
    labels = [summary['models'][m].get('display_name', m) for m in model_ids]
    clean = [safe_float(summary['models'][m].get('clean_map50')) for m in model_ids]
    adverse = [safe_float(summary['models'][m].get('adverse_map50')) for m in model_ids]
    rpc = [safe_float(summary['models'][m].get('rpc50')) for m in model_ids]

    x = np.arange(len(model_ids))
    w = 0.25
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - w, clean, w, label='clean mAP50')
    ax.bar(x, adverse, w, label='adverse mAP50')
    ax.bar(x + w, rpc, w, label='rPC50')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha='right')
    ax.set_ylim(0, 1.05)
    ax.set_title('Policy Metrics by Candidate Model')
    ax.legend()
    save(fig, outdir, 'fig_policy_summary')


def fig_scenario_lines(summary, rows_map, outdir):
    all_ids = sorted({r['scenario_id'] for rows in rows_map.values() for r in rows})
    x = np.arange(len(all_ids))
    fig, ax = plt.subplots(figsize=(max(10, len(all_ids) * 0.8), 5))
    for model_id, rows in rows_map.items():
        display_name = summary['models'][model_id].get('display_name', model_id)
        vals = {r['scenario_id']: safe_float(r.get('map50')) for r in rows}
        ax.plot(x, [vals.get(i, 0) for i in all_ids], marker='o', label=display_name)
    ax.set_xticks(x)
    ax.set_xticklabels(all_ids, rotation=30, ha='right')
    ax.set_ylim(0, 1.05)
    ax.set_title('Scenario-wise mAP50')
    ax.set_ylabel('mAP50')
    ax.legend()
    save(fig, outdir, 'fig_scenario_lines')


def fig_bucket_bars(summary, rows_map, outdir):
    buckets = ['clean_reference', 'operational', 'adverse', 'critical']
    model_ids = list(rows_map.keys())
    x = np.arange(len(buckets))
    width = 0.8 / max(1, len(model_ids))
    fig, ax = plt.subplots(figsize=(10, 5))
    for idx, model_id in enumerate(model_ids):
        rows = rows_map[model_id]
        display_name = summary['models'][model_id].get('display_name', model_id)
        vals = []
        for b in buckets:
            items = [safe_float(r.get('map50')) for r in rows if r.get('bucket') == b]
            vals.append(sum(items) / len(items) if items else 0.0)
        ax.bar(x + idx * width - (len(model_ids) - 1) * width / 2, vals, width, label=display_name)
    ax.set_xticks(x)
    ax.set_xticklabels(buckets, rotation=15)
    ax.set_ylim(0, 1.05)
    ax.set_title('Mean mAP50 by Scenario Bucket')
    ax.legend()
    save(fig, outdir, 'fig_bucket_mAP50')


def main():
    parser = argparse.ArgumentParser(description='Visualize summary outputs from the framework evaluation.')
    parser.add_argument('--summary', required=True)
    parser.add_argument('--outdir', default='framework_figures')
    args = parser.parse_args()

    summary = load_json(Path(args.summary))
    rows_map = load_rows(summary)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fig_policy_summary(summary, outdir)
    fig_scenario_lines(summary, rows_map, outdir)
    fig_bucket_bars(summary, rows_map, outdir)

    print(f'\n[OK] figures written -> {outdir.resolve()}')


if __name__ == '__main__':
    main()

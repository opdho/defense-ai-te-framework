import argparse
from pathlib import Path
from typing import Any, Dict, List

from ultralytics import YOLO

from framework_utils import dump_json, load_json, safe_float, write_csv_rows


def get_metrics(metrics_obj):
    box = metrics_obj.box

    def safe(fn):
        try:
            value = fn()
            return float(value) if value is not None else 0.0
        except Exception:
            return 0.0

    return {
        'precision': safe(lambda: box.mp),
        'recall': safe(lambda: box.mr),
        'map50': safe(lambda: box.map50),
        'map50_95': safe(lambda: box.map),
    }


def load_policy(path: Path) -> Dict[str, Any]:
    policy = load_json(path)
    if 'gates' not in policy:
        raise ValueError('Policy JSON must contain a gates list.')
    return policy


def evaluate_model(weights: Path, scenarios: List[Dict[str, Any]], yaml_dir: Path, device: str, batch: int, imgsz: int, workers: int) -> List[Dict[str, Any]]:
    model = YOLO(str(weights))
    rows = []
    for idx, scn in enumerate(scenarios, 1):
        sid = scn['scenario_id']
        yaml_path = yaml_dir / f'data_{sid}.yaml'
        if not yaml_path.exists():
            print(f'[WARN] missing yaml for {sid}: {yaml_path}')
            continue
        print(
            f"  [{idx:>2}/{len(scenarios)}] {sid} {scn['bucket']:<16} {scn['corruption_family']:<22} ",
            end='',
            flush=True,
        )
        try:
            metrics = get_metrics(
                model.val(
                    data=str(yaml_path),
                    split='val',
                    imgsz=imgsz,
                    batch=batch,
                    device=device,
                    workers=workers,
                    verbose=False,
                    plots=False,
                    save_json=False,
                )
            )
            print(f"mAP50={metrics['map50']:.4f} mAP50-95={metrics['map50_95']:.4f}")
        except Exception as e:
            print(f'ERROR ({e})')
            metrics = {'precision': 0.0, 'recall': 0.0, 'map50': 0.0, 'map50_95': 0.0}

        row = {
            'scenario_id': sid,
            'weather': scn.get('weather', ''),
            'time_of_day': scn.get('time_of_day', ''),
            'target_density': scn.get('target_density', ''),
            'sensor_noise_level': scn.get('sensor_noise_level', 0),
            'adversarial_camouflage': scn.get('adversarial_camouflage', False),
            'visibility_km': scn.get('visibility_km', 0),
            'difficulty': scn.get('difficulty', ''),
            'bucket': scn.get('bucket', ''),
            'corruption_family': scn.get('corruption_family', ''),
            'severity': scn.get('severity', 0),
            'safety_critical': scn.get('safety_critical', False),
            **{k: round(v, 6) for k, v in metrics.items()},
        }
        rows.append(row)
    return rows


def derive_metrics(rows: List[Dict[str, Any]], policy: Dict[str, Any]) -> Dict[str, Any]:
    if not rows:
        return {}

    clean = [r for r in rows if r.get('bucket') == 'clean_reference']
    corrupted = [r for r in rows if r.get('bucket') != 'clean_reference']
    adverse = [r for r in rows if r.get('bucket') in {'adverse', 'critical'}]
    critical = [r for r in rows if r.get('bucket') == 'critical']

    def mean(items, key):
        if not items:
            return 0.0
        return sum(safe_float(x.get(key)) for x in items) / len(items)

    clean_map50 = mean(clean, 'map50')
    clean_map50_95 = mean(clean, 'map50_95')
    clean_precision = mean(clean, 'precision')
    clean_recall = mean(clean, 'recall')
    mpc50 = mean(corrupted, 'map50')
    adverse_map50 = mean(adverse, 'map50')
    worstcase_map50 = min(safe_float(r.get('map50')) for r in rows)
    rpc50 = (mpc50 / clean_map50) if clean_map50 > 1e-9 else 0.0
    adverse_rpc50 = (adverse_map50 / clean_map50) if clean_map50 > 1e-9 else 0.0

    critical_floor = safe_float(policy.get('derived_params', {}).get('critical_failure_floor_map50', 0.2), 0.2)
    critical_failure_count = sum(1 for r in critical if safe_float(r.get('map50')) < critical_floor)

    for r in rows:
        r['clean_map50_reference'] = round(clean_map50, 6)
        r['relative_to_clean'] = round((safe_float(r.get('map50')) / clean_map50) if clean_map50 > 1e-9 else 0.0, 6)
        r['drop_from_clean_pct'] = round(max(0.0, 1.0 - r['relative_to_clean']) * 100.0, 2)

    return {
        'clean_map50': round(clean_map50, 4),
        'clean_map50_95': round(clean_map50_95, 4),
        'clean_precision': round(clean_precision, 4),
        'clean_recall': round(clean_recall, 4),
        'mpc50': round(mpc50, 4),
        'rpc50': round(rpc50, 4),
        'adverse_map50': round(adverse_map50, 4),
        'adverse_rpc50': round(adverse_rpc50, 4),
        'worstcase_map50': round(worstcase_map50, 4),
        'critical_failure_count': int(critical_failure_count),
        'num_scenarios': len(rows),
        'num_clean_reference': len(clean),
        'num_corrupted': len(corrupted),
        'num_critical': len(critical),
        'critical_failure_floor_map50': round(critical_floor, 4),
    }


def compare(left, operator: str, right) -> bool:
    if operator == '>=':
        return left >= right
    if operator == '<=':
        return left <= right
    if operator == '>':
        return left > right
    if operator == '<':
        return left < right
    if operator == '==':
        return left == right
    raise ValueError(f'Unsupported operator: {operator}')


def apply_policy(summary: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    criteria = {}
    passed = True
    for gate in policy.get('gates', []):
        metric_name = gate['metric']
        operator = gate.get('operator', '>=')
        threshold = gate['threshold']
        value = safe_float(summary.get(metric_name))
        ok = compare(value, operator, threshold)
        criteria[gate['id']] = {
            'metric': metric_name,
            'description': gate.get('description', ''),
            'value': round(value, 4),
            'operator': operator,
            'threshold': threshold,
            'pass': ok,
        }
        passed = passed and ok
    return {
        'policy_id': policy.get('policy_id', 'unknown'),
        'policy_name': policy.get('display_name', ''),
        'overall_judgment': 'PASS' if passed else 'FAIL',
        'cicd_deployable': passed,
        'criteria': criteria,
        **summary,
    }


def print_decision(model_name: str, summary: Dict[str, Any]) -> None:
    icon = '✅ PASS' if summary['overall_judgment'] == 'PASS' else '❌ FAIL'
    print(f"\n[{model_name}] -> {icon}")
    print('─' * 72)
    for cid, crit in summary['criteria'].items():
        icon2 = '✅' if crit['pass'] else '❌'
        print(
            f"  {icon2} {cid:<28} {crit['metric']:<24} "
            f"{crit['value']:>7.4f} {crit['operator']} {crit['threshold']}"
        )
    print(f"\n  clean_map50           : {summary['clean_map50']:.4f}")
    print(f"  clean_map50_95        : {summary['clean_map50_95']:.4f}")
    print(f"  mPC50                 : {summary['mpc50']:.4f}")
    print(f"  rPC50                 : {summary['rpc50']:.4f}")
    print(f"  adverse_map50         : {summary['adverse_map50']:.4f}")
    print(f"  worstcase_map50       : {summary['worstcase_map50']:.4f}")
    print(f"  critical_failure_count: {summary['critical_failure_count']}")
    print(f"  CI/CD deployable      : {'YES' if summary['cicd_deployable'] else 'NO'}")


def main():
    parser = argparse.ArgumentParser(description='Evaluate all registered candidate models against scenario-generated M&S datasets.')
    parser.add_argument('--registry', required=True)
    parser.add_argument('--yaml-dir', required=True)
    parser.add_argument('--scenarios', required=True)
    parser.add_argument('--policy', required=True)
    parser.add_argument('--device', default='0')
    parser.add_argument('--batch', type=int, default=8)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--outdir', default='framework_eval')
    args = parser.parse_args()

    registry = load_json(Path(args.registry))
    policy = load_policy(Path(args.policy))
    scenarios = load_json(Path(args.scenarios))
    yaml_dir = Path(args.yaml_dir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    models = registry.get('models', [])
    if not models:
        raise ValueError('No models were found in the registry.')

    comparison = {
        'policy': {
            'policy_id': policy.get('policy_id'),
            'display_name': policy.get('display_name'),
        },
        'models': {},
    }

    print('=' * 76)
    print('Scenario-based automated T&E for registered models')
    print(f"Policy: {policy.get('display_name', policy.get('policy_id', 'unknown'))}")
    print('=' * 76)

    for model_cfg in models:
        model_id = model_cfg['model_id']
        model_name = model_cfg.get('display_name', model_id)
        weights = Path(model_cfg['weights'])
        if not weights.exists():
            print(f'[WARN] weights not found for {model_id}: {weights}')
            continue

        print(f"\n{'=' * 76}\nEvaluating {model_name} ({weights})\n{'=' * 76}")
        rows = evaluate_model(weights, scenarios, yaml_dir, args.device, args.batch, args.imgsz, args.workers)
        summary = derive_metrics(rows, policy)
        decision = apply_policy(summary, policy)
        decision['model_id'] = model_id
        decision['display_name'] = model_name
        decision['weights'] = str(weights)
        decision['notes'] = model_cfg.get('notes', '')

        csv_path = outdir / f'eval_results_{model_id}.csv'
        write_csv_rows(rows, csv_path)
        decision['results_csv'] = str(csv_path)
        comparison['models'][model_id] = decision
        print_decision(model_name, decision)
        print(f'[OK] wrote {csv_path}')

    cmp_path = outdir / 'evaluation_summary.json'
    dump_json(comparison, cmp_path)
    print(f"\n[OK] summary written -> {cmp_path}")
    print('[NEXT] python 04_generate_llm_feedback_reports.py --registry ... --summary framework_eval/evaluation_summary.json')


if __name__ == '__main__':
    main()

import argparse
from datetime import datetime
from pathlib import Path

from framework_utils import dump_json, load_json


class C:
    G = '\033[92m'
    R = '\033[91m'
    Y = '\033[93m'
    C = '\033[96m'
    B = '\033[1m'
    E = '\033[0m'


def log(msg, level='INFO', color=''):
    ts = datetime.now().strftime('%H:%M:%S')
    icons = {'INFO': 'ℹ', 'OK': '✅', 'FAIL': '❌', 'WARN': '⚠', 'STEP': '▶'}
    line = f"[{ts}][{icons.get(level, '?')} {level:4s}] {msg}"
    print(f'{color}{line}{C.E}')
    return line


def stage(n, name):
    print(f"\n{C.C}{C.B}{'='*64}\n  Stage {n}: {name}\n{'─'*64}{C.E}")


def run_pipeline(model_id: str, model_cfg: dict, decision: dict, logs: list):
    display_name = model_cfg.get('display_name', model_id)
    print(f"\n{C.B}{'▓'*64}\n  Processing: {display_name}\n{'▓'*64}{C.E}")

    stage(1, 'Model Registration & Provenance')
    version = datetime.now().strftime('v%Y%m%d-%H%M')
    commit = f"{hash(display_name) & 0xFFFFFF:06x}"
    logs.append(log(f'registered model={display_name} version={version} commit={commit}', 'OK', C.G))
    logs.append(log(f"weights={model_cfg.get('weights', 'N/A')}", 'INFO'))

    stage(2, 'Build & Package')
    logs.append(log('model artifact integrity check passed', 'OK', C.G))
    logs.append(log('runtime package manifest created [SIMULATED]', 'OK', C.G))

    stage(3, 'Security, Signing & Compliance')
    for item in ['malware scan', 'dependency audit', 'artifact signing', 'SBOM export']:
        logs.append(log(f'{item}: passed', 'OK', C.G))

    stage(4, 'Automated M&S T&E')
    logs.append(log(f"policy={decision.get('policy_name', decision.get('policy_id', 'policy'))}", 'INFO'))
    logs.append(log(f"clean_map50={decision.get('clean_map50', 0):.4f}", 'INFO'))
    logs.append(log(f"mPC50={decision.get('mpc50', 0):.4f}", 'INFO'))
    logs.append(log(f"rPC50={decision.get('rpc50', 0):.4f}", 'INFO'))
    logs.append(log(f"adverse_map50={decision.get('adverse_map50', 0):.4f}", 'INFO'))
    logs.append(log(f"critical_failure_count={decision.get('critical_failure_count', 0)}", 'INFO'))
    for cid, crit in decision.get('criteria', {}).items():
        icon = '✅' if crit.get('pass') else '❌'
        logs.append(log(f"{icon} {cid}: {crit['metric']} {crit['operator']} {crit['threshold']} (observed={crit['value']})", 'INFO'))

    stage(5, 'Gate Decision')
    if decision.get('cicd_deployable'):
        logs.append(log(f'{display_name} gate PASSED', 'OK', C.G))
        logs.append(log('promotion to staging approved', 'OK', C.G))
    else:
        logs.append(log(f'{display_name} gate FAILED', 'FAIL', C.R))
        logs.append(log('automatic deployment blocked', 'FAIL', C.R))
        stage(6, 'Feedback Loop')
        logs.append(log('feedback report attached for remediation', 'WARN', C.Y))
        logs.append(log('candidate returned to training or replacement queue', 'WARN', C.Y))
        return None

    stage(6, 'Staging Deployment')
    logs.append(log('staging deployment simulated successfully', 'OK', C.G))
    logs.append(log('smoke test passed', 'OK', C.G))

    stage(7, 'Operational Deployment')
    manifest = {
        'model_id': model_id,
        'display_name': display_name,
        'version': version,
        'commit': commit,
        'deployment_time': datetime.now().isoformat(),
        'judgment': 'PASS',
        'policy_id': decision.get('policy_id'),
        'clean_map50': decision.get('clean_map50'),
        'mpc50': decision.get('mpc50'),
        'rpc50': decision.get('rpc50'),
        'adverse_map50': decision.get('adverse_map50'),
        'status': 'DEPLOYED',
    }
    logs.append(log(f'{display_name} operational deployment completed', 'OK', C.G))
    return manifest


def main():
    parser = argparse.ArgumentParser(description='Simulate a DevSecOps CI/CD gate using evaluation summary.')
    parser.add_argument('--registry', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--out-log', default='framework_cicd_log.txt')
    parser.add_argument('--out-manifest', default='framework_deployment_manifest.json')
    args = parser.parse_args()

    registry = load_json(Path(args.registry))
    summary = load_json(Path(args.summary))
    model_map = {m['model_id']: m for m in registry.get('models', [])}
    logs = []
    manifests = []

    print(f"\n{C.B}{'#'*64}")
    print('  DevSecOps CI/CD — Scenario-based AI T&E Framework')
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*64}{C.E}\n")

    for model_id, decision in summary.get('models', {}).items():
        model_cfg = model_map.get(model_id, {})
        result = run_pipeline(model_id, model_cfg, decision, logs)
        if result:
            manifests.append(result)

    Path(args.out_log).write_text('\n'.join(logs), encoding='utf-8')
    dump_json(manifests, Path(args.out_manifest))

    print(f"\n{C.B}{'='*64}")
    print('  PIPELINE SUMMARY')
    print(f"{'='*64}{C.E}")
    for model_id, decision in summary.get('models', {}).items():
        display_name = model_map.get(model_id, {}).get('display_name', model_id)
        icon = '✅ DEPLOYED' if decision.get('cicd_deployable') else '❌ BLOCKED '
        print(f"  {display_name:24s} {icon}  rPC50={decision.get('rpc50', 0):.4f}  adverse_map50={decision.get('adverse_map50', 0):.4f}")

    print(f"\n[OK] {args.out_log} / {args.out_manifest} written")
    print('[NEXT] python 06_visualize_summary.py --summary framework_eval/evaluation_summary.json')


if __name__ == '__main__':
    main()

import argparse
import json
from datetime import datetime
from pathlib import Path

import requests

from framework_utils import load_csv_rows, load_json, safe_float


def call_ollama(host: str, model: str, system_prompt: str, user_content: str) -> str:
    r = requests.post(
        f'{host}/api/chat',
        json={
            'model': model,
            'stream': False,
            'think': False,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content},
            ],
        },
        timeout=180,
    )
    r.raise_for_status()
    return r.json()['message']['content']


def build_template_report(model_name: str, decision: dict, rows: list, policy: dict) -> str:
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    is_pass = decision['overall_judgment'] == 'PASS'
    policy_name = decision.get('policy_name', policy.get('display_name', 'policy'))
    worst = sorted(rows, key=lambda r: safe_float(r.get('map50')))[:5]
    failed_criteria = [v for v in decision.get('criteria', {}).values() if not v.get('pass')]
    strong_criteria = [v for v in decision.get('criteria', {}).values() if v.get('pass')]

    lines = [
        '#' * 74,
        f"Framework T&E Feedback Report — {'PASS' if is_pass else 'FAIL'}",
        '#' * 74,
        f'model          : {model_name}',
        f'evaluation time: {now}',
        f'policy         : {policy_name}',
        f"judgment       : {decision['overall_judgment']}",
        '',
        '1. Executive Summary',
        f"  - clean_map50           : {decision.get('clean_map50', 0):.4f}",
        f"  - clean_map50_95        : {decision.get('clean_map50_95', 0):.4f}",
        f"  - mPC50                 : {decision.get('mpc50', 0):.4f}",
        f"  - rPC50                 : {decision.get('rpc50', 0):.4f}",
        f"  - adverse_map50         : {decision.get('adverse_map50', 0):.4f}",
        f"  - worstcase_map50       : {decision.get('worstcase_map50', 0):.4f}",
        f"  - critical_failure_count: {decision.get('critical_failure_count', 0)}",
        '',
        '2. Gate Decision Basis',
    ]
    for crit in decision.get('criteria', {}).values():
        icon = 'PASS' if crit['pass'] else 'FAIL'
        lines.append(
            f"  - {icon}: {crit['metric']} {crit['operator']} {crit['threshold']} "
            f"(observed {crit['value']:.4f})"
        )

    if is_pass:
        lines += [
            '',
            '3. Deployment Recommendation',
            '  This model satisfies the selected T&E policy and can proceed to staging deployment.',
            '  Continue post-deployment monitoring for performance drift and new scenario failures.',
            '',
            '4. Strongest Areas',
        ]
        for crit in strong_criteria[:4]:
            lines.append(f"  - {crit['metric']}: stable against gate requirement ({crit['value']:.4f})")
    else:
        lines += [
            '',
            '3. Failure Diagnosis',
            '  The model did not meet one or more robustness gates and should be blocked from automatic deployment.',
            '',
            '4. Primary Remediation Targets',
        ]
        for crit in failed_criteria[:4]:
            lines.append(
                f"  - {crit['metric']}: observed {crit['value']:.4f}, required {crit['operator']} {crit['threshold']}"
            )

    lines += ['', '5. Worst-case Scenarios']
    for r in worst:
        lines.append(
            f"  - [{r['scenario_id']}] {r['bucket']}/{r['corruption_family']} "
            f"mAP50={safe_float(r.get('map50')):.4f} relative_to_clean={safe_float(r.get('relative_to_clean')):.4f}"
        )

    lines += ['', '6. Suggested Next Actions']
    if is_pass:
        lines += [
            '  - promote to staging in the CI/CD pipeline',
            '  - archive evaluation artifacts for auditability',
            '  - schedule periodic re-evaluation when the model or scenario library changes',
        ]
    else:
        lines += [
            '  - augment training or adaptation data for failed corruption families',
            '  - retrain or swap candidate weights, then rerun the same automated scenario suite',
            '  - review critical scenarios with human operators before redefining policy thresholds',
        ]
    lines += ['', '#' * 74]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate model feedback reports after automated T&E.')
    parser.add_argument('--registry', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--policy', required=True)
    parser.add_argument('--outdir', default='framework_reports')
    parser.add_argument('--use-llm', action='store_true')
    parser.add_argument('--host', default='http://localhost:11434')
    parser.add_argument('--model', default='qwen3:4b')
    args = parser.parse_args()

    registry = load_json(Path(args.registry))
    summary = load_json(Path(args.summary))
    policy = load_json(Path(args.policy))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    model_map = {m['model_id']: m for m in registry.get('models', [])}
    for model_id, decision in summary.get('models', {}).items():
        rows = load_csv_rows(Path(decision['results_csv']))
        model_cfg = model_map.get(model_id, {})
        model_name = model_cfg.get('display_name', model_id)

        if args.use_llm:
            sys_prompt = (
                'You are a defense AI T&E analyst. Write a concise, formal Korean report '
                'that explains the automated scenario-based evaluation result and the CI/CD gate decision.'
            )
            user_payload = {
                'model_name': model_name,
                'decision': decision,
                'policy': policy,
                'worst_cases': sorted(rows, key=lambda r: safe_float(r.get('map50')))[:5],
            }
            try:
                text = call_ollama(args.host, args.model, sys_prompt, json.dumps(user_payload, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f'[WARN] LLM report generation failed for {model_id}: {e}. Falling back to template.')
                text = build_template_report(model_name, decision, rows, policy)
        else:
            text = build_template_report(model_name, decision, rows, policy)

        out_txt = outdir / f'report_{model_id}.txt'
        out_md = outdir / f'report_{model_id}.md'
        out_txt.write_text(text, encoding='utf-8')
        out_md.write_text(f"# {model_name} — {decision['overall_judgment']}\n\n```\n{text}\n```\n", encoding='utf-8')
        print(f'[OK] wrote {out_txt} / {out_md}')

    print('\n[NEXT] python 05_simulate_cicd_gate.py --registry ... --summary ...')


if __name__ == '__main__':
    main()

#!/bin/bash
# E2: scenario manifest from E1 (best_manifest_llm.json) -> seeded degradation (seed 0) -> evaluate A/B -> CI/CD gate
cd /d/park/test5
R="C:/Users/PC/AppData/Local/Temp/claude/D--park-test5/c7edb9fc-e677-4b59-9dd6-ee7b7ac885fe/scratchpad/run.sh"
PY=/d/miniconda3/envs/test5_revision/python.exe
export PYTHONUTF8=1 PYTHONUNBUFFERED=1
bash "$R" "$PY revision/02_generate_ms_eval_dataset_seeded.py --scenarios revision/llm_trials/best_manifest_llm.json --val-images revision/data/Defense_AI_4cls/val/images --val-labels revision/data/Defense_AI_4cls/val/labels --output revision/datasets/llm_seed0 --yaml-dir revision/yaml/llm_seed0 --meta-out revision/meta/llm_seed0.json --seed 0 > revision/logs/E2_gen_llm_seed0.log 2>&1" || exit 1
bash "$R" "$PY 03_evaluate_registry.py --registry revision/registry_AB.json --yaml-dir revision/yaml/llm_seed0 --scenarios revision/meta/llm_seed0.json --policy policy_profiles/policy_nist_coco_robustness_demo.json --device 0 --outdir revision/eval/llm_seed0 > revision/logs/E2_eval_llm_seed0.log 2>&1" || exit 2
bash "$R" "$PY 05_simulate_cicd_gate.py --registry revision/registry_AB.json --summary revision/eval/llm_seed0/evaluation_summary.json --out-log revision/eval/llm_seed0/cicd_log.txt --out-manifest revision/eval/llm_seed0/deploy_manifest.json > revision/logs/E2_gate_llm_seed0.log 2>&1" || exit 3
echo E2_DONE

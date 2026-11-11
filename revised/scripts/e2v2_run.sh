#!/bin/bash
# E2 (v2): first passing E1 v2 manifest -> seeded degradation (seed 0) -> evaluate 4 models (registry_2x2) -> CI/CD gate
cd /d/park/test5
R="C:/Users/PC/AppData/Local/Temp/claude/D--park-test5/c7edb9fc-e677-4b59-9dd6-ee7b7ac885fe/scratchpad/run.sh"
PY=/d/miniconda3/envs/test5_revision/python.exe
export PYTHONUTF8=1 PYTHONUNBUFFERED=1
[ -f revision/llm_trials_v2/best_manifest_llm_v2.json ] || { echo "no v2 manifest"; exit 9; }
bash "$R" "$PY revision/02_generate_ms_eval_dataset_seeded.py --scenarios revision/llm_trials_v2/best_manifest_llm_v2.json --val-images revision/data/Defense_AI_4cls/val/images --val-labels revision/data/Defense_AI_4cls/val/labels --output revision/datasets/llm_v2_seed0 --yaml-dir revision/yaml/llm_v2_seed0 --meta-out revision/meta/llm_v2_seed0.json --seed 0 > revision/logs/E2v2_gen_seed0.log 2>&1" || exit 1
bash "$R" "$PY 03_evaluate_registry.py --registry revision/registry_2x2.json --yaml-dir revision/yaml/llm_v2_seed0 --scenarios revision/meta/llm_v2_seed0.json --policy policy_profiles/policy_nist_coco_robustness_demo.json --device 0 --outdir revision/eval/llm_v2_seed0 > revision/logs/E2v2_eval_seed0.log 2>&1" || exit 2
bash "$R" "$PY 05_simulate_cicd_gate.py --registry revision/registry_2x2.json --summary revision/eval/llm_v2_seed0/evaluation_summary.json --out-log revision/eval/llm_v2_seed0/cicd_log.txt --out-manifest revision/eval/llm_v2_seed0/deploy_manifest.json > revision/logs/E2v2_gate_seed0.log 2>&1" || exit 3
echo E2V2_DONE

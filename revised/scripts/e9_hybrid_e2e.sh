#!/bin/bash
# E9: one run through all 8 stages of the recommended configuration (expert-fixed mission-critical + LLM variation).
# Stops at the first failed step. Each step is timed in revision/logs/E9_timeline.log and logged in RUN_COMMANDS.md.
cd "${PROJECT_ROOT:-.}" || exit 1
R=revision/scripts/run_logged.sh
PY=${PY:-python}
TL=revision/logs/E9_timeline.log
EVAL=revision/eval/e9_hybrid_seed0
export PYTHONUTF8=1 PYTHONUNBUFFERED=1
mkdir -p "$EVAL"

step() {
  local name="$1" cmd="$2" s rc
  s=$(date '+%Y-%m-%d %H:%M:%S')
  bash "$R" "$cmd"
  rc=$?
  echo "$name | start $s | end $(date '+%Y-%m-%d %H:%M:%S') | exit $rc" >> "$TL"
  [ $rc -eq 0 ] || { echo "E9_FAILED at $name (exit $rc)" >> "$TL"; exit $rc; }
}

echo "E9 start $(date '+%Y-%m-%d %H:%M:%S') ollama=$(curl -s -m 5 localhost:11434/api/version)" >> "$TL"
step 1a_generate "$PY revision/07b_llm_scenario_trials_v2.py scenarios --model gemma4:12b --runs 1 --seed0 2000 --outdir revision/llm_e9 > revision/logs/E9_1_generate.log 2>&1"
step 1b_compare_run0 "$PY revision/scripts/e9_compare_run0.py > revision/logs/E9_1b_compare.log 2>&1"
step 2_compose "$PY revision/scripts/e9_compose_manifest.py > revision/logs/E9_2_compose.log 2>&1"
step 3_g0_precheck "$PY revision/scripts/e9_g0_precheck.py > revision/logs/E9_3_g0.log 2>&1"
step 4_degrade "$PY revision/02_generate_ms_eval_dataset_seeded.py --scenarios revision/llm_e9/hybrid_manifest.json --val-images revision/data/Defense_AI_4cls/val/images --val-labels revision/data/Defense_AI_4cls/val/labels --output revision/datasets/e9_hybrid_seed0 --yaml-dir revision/yaml/e9_hybrid_seed0 --meta-out revision/meta/e9_hybrid_seed0.json --seed 0 > revision/logs/E9_4_degrade.log 2>&1"
step 5_evaluate "$PY 03_evaluate_registry.py --registry revision/registry_6.json --yaml-dir revision/yaml/e9_hybrid_seed0 --scenarios revision/meta/e9_hybrid_seed0.json --policy policy_profiles/policy_nist_coco_robustness_demo.json --device 0 --outdir $EVAL > revision/logs/E9_5_evaluate.log 2>&1"
step 6_gate "$PY revision/05b_gate_with_coverage.py --registry revision/registry_6.json --summary $EVAL/evaluation_summary.json --scenarios revision/meta/e9_hybrid_seed0.json --required revision/policy/mission_critical_required.json --out-log $EVAL/cicd_log.txt --out-manifest $EVAL/deploy_manifest.json --out-verdict $EVAL/verdict.json > revision/logs/E9_6_gate.log 2>&1"
step 7a_reports "$PY 04_generate_llm_feedback_reports.py --registry revision/registry_6.json --summary $EVAL/evaluation_summary.json --policy policy_profiles/policy_nist_coco_robustness_demo.json --use-llm --model gemma4:12b --outdir revision/reports_e9 > revision/logs/E9_7_reports.log 2>&1"
step 7b_report_check "$PY revision/07_llm_scenario_trials.py report-check --summary $EVAL/evaluation_summary.json --reports revision/reports_e9 > revision/logs/E9_7_report_check.log 2>&1"
step 8_manifest "cat $EVAL/deploy_manifest.json > revision/logs/E9_8_manifest.log"
echo "E9_DONE $(date '+%Y-%m-%d %H:%M:%S')" >> "$TL"

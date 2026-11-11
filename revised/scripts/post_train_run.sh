#!/bin/bash
# After the E4 retrain: registries -> E4 eval of A_rep/C_clean/B_rep on the submission eval set -> E5 (seeds 0-4, 7 models).
# E5 seed 0 reuses the E2-fallback set (revision/yaml/llm_seed0, revision/meta/llm_seed0.json; identical to scenario_manifest seed 0).
# Seeds 1-4 are generated with scenario_manifest.json; generation of seed k+1 (CPU) runs while seed k is evaluated (GPU).
# Every step goes through run_logged.sh (one row each in RUN_COMMANDS.md). Progress markers -> revision/logs/post_train_chain.log
cd "${PROJECT_ROOT:-.}" || exit 1
R=revision/scripts/run_logged.sh
PY=${PY:-python}
POL=policy_profiles/policy_nist_coco_robustness_demo.json
VI=revision/data/Defense_AI_4cls/val/images
VL=revision/data/Defense_AI_4cls/val/labels
CL=revision/logs/post_train_chain.log
export PYTHONUTF8=1 PYTHONUNBUFFERED=1
mark() { echo "$(date '+%F %T') $*" >> $CL; }

gen() {  # seed k
  local k=$1
  bash $R "$PY revision/02_generate_ms_eval_dataset_seeded.py --scenarios scenario_manifest.json --val-images $VI --val-labels $VL --output revision/datasets/preset_seed$k --yaml-dir revision/yaml/preset_seed$k --meta-out revision/meta/preset_seed$k.json --seed $k > revision/logs/E5_gen_seed$k.log 2>&1"
}
evalgate() {  # registry yaml meta outdir logtag
  bash $R "$PY 03_evaluate_registry.py --registry $1 --yaml-dir $2 --scenarios $3 --policy $POL --device 0 --outdir $4 > revision/logs/$5_eval.log 2>&1" || return 1
  bash $R "$PY 05_simulate_cicd_gate.py --registry $1 --summary $4/evaluation_summary.json --out-log $4/cicd_log.txt --out-manifest $4/deploy_manifest.json > revision/logs/$5_gate.log 2>&1"
}

mark "START"
bash $R "$PY revision/scripts/make_registries.py --out-retrain revision/registry_retrain.json --out-7 revision/registry_7.json > revision/logs/make_registries.log 2>&1" || { mark "FAIL make_registries"; exit 1; }

# E4: retrained models on the submission eval set (same images as revision/eval/2x2_submitted_set)
evalgate revision/registry_retrain.json dataset_yaml_framework scenario_metadata_framework.json revision/eval/2x2_retrain E4_retrain && mark "E4 eval done" || mark "FAIL E4 eval"

# E5
gen 1 & GP=$!
evalgate revision/registry_7.json revision/yaml/llm_seed0 revision/meta/llm_seed0.json revision/eval/preset_seed0 E5_seed0 && mark "E5 seed0 done" || mark "FAIL E5 seed0"
for k in 1 2 3 4; do
  wait $GP; rc=$?
  if [ $k -lt 4 ]; then gen $((k+1)) & GP=$!; fi
  [ $rc -ne 0 ] && { mark "FAIL gen seed$k rc=$rc"; continue; }
  mark "gen seed$k done"
  evalgate revision/registry_7.json revision/yaml/preset_seed$k revision/meta/preset_seed$k.json revision/eval/preset_seed$k E5_seed$k && mark "E5 seed$k done" || mark "FAIL E5 seed$k"
done
mark "POST_TRAIN_DONE"

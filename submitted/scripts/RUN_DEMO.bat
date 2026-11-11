
@echo off
REM Main framework demo (using already prepared weights)
REM Set DATASET to the dataset folder first, e.g. set DATASET=C:\data\Defense_AI_Dataset
if not defined DATASET (echo Set DATASET to the dataset folder & exit /b 1)
python 01_generate_scenarios_llm.py --mode preset --out scenario_manifest.json
python 02_generate_ms_eval_dataset.py --scenarios scenario_manifest.json --val-images %DATASET%/val/images --val-labels %DATASET%/val/labels --output dataset/ms_eval_framework --yaml-dir dataset_yaml_framework
python 03_evaluate_registry.py --registry model_registry.json --yaml-dir dataset_yaml_framework --scenarios scenario_metadata_framework.json --policy policy_profiles/policy_nist_coco_robustness_demo.json --device 0
python 04_generate_llm_feedback_reports.py --registry model_registry.json --summary framework_eval/evaluation_summary.json --policy policy_profiles/policy_nist_coco_robustness_demo.json
python 05_simulate_cicd_gate.py --registry model_registry.json --summary framework_eval/evaluation_summary.json
python 06_visualize_summary.py --summary framework_eval/evaluation_summary.json
pause

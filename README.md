# Automated T&E framework for defense AI object detection: experiment artifacts

Artifacts for the paper:

> Park, D., Kim, D., & Yoon, Y. (2026). DevSecOps 환경에서 LLM 기반 시나리오 생성과 열화 평가를 연계한 국방 AI 객체탐지 모델 자동 시험평가 프레임워크. *Journal of Defense Quality Society* (국방품질연구논집). (Volume, issue and pages to be added.)

본 저장소는 위 논문의 실험 산출물(시나리오별 평가 결과, 시나리오 매니페스트, 정책 게이트 설정, 학습 설정, 그림 생성 스크립트)을 공개합니다. 투고본(`submitted/`)과 수정·게재본(`revised/`)의 산출물을 구분하여 수록하였습니다.

## Layout

| Folder | Contents |
|---|---|
| `submitted/` | The submitted manuscript's run: framework scripts (01–06), preset scenario manifest, policy profile, per-scenario CSVs for the submitted models A and B, Stage 7 reports, CI/CD log, and the original figure files used as Figures 2–4 of the submitted manuscript; training data YAML of the submitted model B (`config/data_model_B.yaml`, trained on a different machine). |
| `submitted/verify_submitted_figures.py` | Reads the plotted coordinates of the submitted Figures 2 and 3 from the vector PDFs and compares them with the CSVs. Output: `submitted/VERIFY_SUBMITTED_FIGURES.md`. |
| `revised/scripts/` | Scripts added for the revision: seeded corruption generation, LLM scenario-generation trials (three-layer guardrail), 4-class dataset build/verification, G0 coverage pre-check, hybrid manifest composition, training batch files. |
| `revised/config/` | Model registries, G0 mission-critical condition list, scenario metadata per run, per-scenario evaluation YAMLs, training arguments (`args.yaml`) and training curves (`results.csv`) of the four models, training data YAMLs (`training_data/`), dataset statistics, Python package list. |
| `revised/results/eval/` | Per-scenario CSVs, `evaluation_summary.json`, deployment manifests and CI/CD logs for every evaluation run in the paper. |
| `revised/results/llm_trials/` | LLM scenario-generation trials (30 runs per condition): every attempt (`attempts.jsonl`), generated manifests, per-run metrics, and the recommended-configuration (E9) manifests. |
| `revised/results/llm_reports/` | Stage 7 LLM feedback reports. |
| `revised/figures/` | `make_tables.py` rebuilds `tables.json` (all numbers in the paper's tables) from the CSVs; `make_figures.py` draws Figures 2–4 of the paper into `output/`. |
| `revised/results/logs/` | Timeline of the single eight-stage run and report-check logs. |
| `revised/RUN_COMMANDS.md` | Every command run for the revision, with start/end time and exit code. |

## Model names in the paper and in the files

| Paper | Architecture / recipe | Per-scenario CSV (preset scenarios) | Training settings |
|---|---|---|---|
| A | YOLO11n / base | `revised/results/eval/2x2_retrain/eval_results_model_A_rep.csv` | `revised/config/training/model_A_rep/` |
| B | YOLO11s / robust | `revised/results/eval/2x2_retrain/eval_results_model_B_rep.csv` | `revised/config/training/model_B_rep/` |
| C | YOLO11n / robust | `revised/results/eval/2x2_retrain/eval_results_model_C_clean.csv` | `revised/config/training/model_C_clean/` |
| D | YOLO11s / base | `revised/results/eval/2x2_submitted_set/eval_results_model_D.csv` | `revised/config/training/model_D_s_base/` |
| Submitted A, B | YOLO11n / base, YOLO11s / robust | `submitted/results/framework_eval/eval_results_model_{A,B}.csv` | trained on a different machine with the same settings |

`revised/results/eval/2x2_submitted_set/eval_results_model_{A,B}.csv` are the submitted models re-evaluated on the same evaluation images as the submitted run (maximum difference from the submitted CSVs: 0.0003). In `tables.json`, the keys `A'`, `B'`, `C`, `D` are the paper's A, B, C, D, and `A`, `B` are the submitted models.

Five corruption seeds: `revised/results/eval/preset_seed{0..4}/`. LLM-only set (gemma4:12b): `llm_gemma4_12b_seed0/`. Recommended configuration (expert-fixed critical scenarios + LLM scenarios, G0 check): `e9_hybrid_seed0/`.

`llm_seed0/` is the first end-to-end run with qwen3:4b; every L1+L2+L3 run fell back to the preset scenarios (`llm_trials/summary.json`, fallback_rate 1.0), so its A/B CSVs are identical to `preset_seed0/`.

## Where each result in the paper comes from

| Paper | Source in this repository |
|---|---|
| Tables 6, 8, 9, 10 and Figures 2–4 | `revised/figures/make_tables.py` → `tables.json` → `make_figures.py` (from `revised/results/eval/`) |
| Table 11 (guardrail trials) | `revised/results/llm_trials/*/summary.json`, `trial_metrics.csv`, `attempts.jsonl` |
| Table 12 (LLM-only set vs. recommended configuration) | `revised/results/eval/llm_gemma4_12b_seed0/`, `e9_hybrid_seed0/` (`tables.json` keys `e7`, `e9`) |
| Table 13 (rule compliance vs. coverage) | `revised/results/e8_gate_verification/verification.json` (`c_manifests`), produced by `revised/scripts/e8_verify.py` |
| Table 14 (Stage 7 report issues) | Reports in `revised/results/llm_reports/`; issues were counted by reading the reports, with `07_llm_scenario_trials.py report-check` as an aid (`revised/results/logs/`) |
| Single eight-stage run (53 min 26 s) | `revised/results/logs/E9_timeline.log` |
| Submitted manuscript, Figures 2–4 | `submitted/` (see the section below) |

## Figures of the submitted manuscript

Figures 2, 3 and 4 of the submitted manuscript are `submitted/figures/fig_scenario_lines.png`, `fig_bucket_mAP50.png` and `fig_policy_summary.png`. They were written by `submitted/scripts/06_visualize_summary.py` from `submitted/results/framework_eval/evaluation_summary.json` and `eval_results_model_{A,B}.csv`. The images embedded in the submitted manuscript file are pixel-identical to these PNGs apart from JPEG compression (mean absolute difference below 1.4 grey levels out of 255).

`verify_submitted_figures.py` reads the plotted points and bars from the matching vector PDFs and compares them with the CSVs; all differences are below 0.0001 (see `submitted/VERIFY_SUBMITTED_FIGURES.md`). In Figure 3, the adverse bucket bar averages SCN_007–010 only, while the policy metric adverse_map50 averages SCN_007–012. The revised paper's Figure 3 caption states this.

SHA-256 (first 16 hex digits): `fig_scenario_lines.png` a5c34ec4d1ce5d69, `fig_bucket_mAP50.png` 38d6f0ec2d7f29df, `fig_policy_summary.png` 4696c33b9ab8b2fa.

## Dataset

Source: Military Assets Dataset (12 classes – YOLOv8 format), Kaggle: https://www.kaggle.com/datasets/rawsi18/military-assets-dataset-12-classes-yolo8-format

Images are not redistributed here; download them from the source under its license. The 4-class set keeps only the boxes of original class ids 2 (military_tank), 3 (military_truck), 4 (military_vehicle) and 6 (soldier), remapped to 0–3, and drops images with none of these classes (`revised/scripts/build_4cls_dataset.py`, `verify_4cls_dataset.py`; counts in `revised/config/dataset_and_env/`). The preset evaluation images are generated from the validation split by `submitted/scripts/02_generate_ms_eval_dataset.py`; the five corruption seeds of the revision (`preset_seed0`–`4`) and the LLM-scenario sets by `revised/scripts/02_generate_ms_eval_dataset_seeded.py`.

License: CC BY 4.0 (Kaggle, owner RAWx18 / Ryan Madhuwala). Images are not redistributed here.

## Reproducing the paper's tables and figures

```bash
pip install matplotlib numpy pdfplumber
python revised/figures/make_tables.py      # writes revised/figures/tables.json
python revised/figures/make_figures.py     # writes revised/figures/output/fig2..fig4
python submitted/verify_submitted_figures.py
```

Re-running training or evaluation requires the dataset, Ultralytics 8.4.21 and a GPU (package list: `revised/config/dataset_and_env/E0_pip_freeze_test5_revision.txt`); LLM trials require Ollama 0.35.0 with the models listed in `revised/results/llm_trials/ollama_model_info/`.

## Notes and limitations

- Paths inside logs, YAML and `args.yaml` files are the original absolute Windows paths of the experiment machine; change them to your local paths.
- Model weights (`.pt`) and evaluation images are not included.
- The robust recipe's 2,340 augmented training images (13 types × 180) were produced before the revision, and the script that generated them was not preserved. Their composition (type, source image) and pixel statistics are given in `revised/config/dataset_and_env/E0_augmented_model_B_by_type.json`, `E0_augmented_model_B_stats.json` and `augB_pixel_stats_vs_source.json`. A search of the experiment machine's drive did not find it. `submitted/scripts/90_optional_build_robust_trainset.py` is a different, optional demo helper (6 types × 120 images) and was not used for these images.
- The CI/CD build, security-scan and deployment steps are simulated by log entries, as stated in the paper.
- `e2_run.sh`, `e2v2_run.sh` and `e2main_run.sh` call a temporary copy of the command-logging wrapper (`$R`, a path under the AI coding assistant's scratch folder). Its content is the same as `revised/scripts/run_logged.sh`; replace `$R` with that script to re-run.

## License

Code (`*.py`, `*.sh`, `*.bat`) is licensed under AGPL-3.0, consistent with Ultralytics YOLO (AGPL-3.0), which the scripts import. Results, figures and documentation are licensed under CC BY 4.0. The dataset (CC BY 4.0) and the Ollama models (Apache-2.0) keep their own licenses.

#!/bin/bash
# E4 training, attempt 2 continued: C resume (epochs 61-70) -> D (yolo11s + base recipe), workers 4 for both.
# Replaces the rest of run_E4_train.bat after C stalled at close_mosaic.
# Step start/end/exit -> revision/logs/E4_train_timeline.log
cd "${PROJECT_ROOT:-.}" || exit 1
PY=${PY:-python}
PROJECT="$(pwd)/revision/runs"  # absolute, so Ultralytics does not nest it under runs/detect
TL=revision/logs/E4_train_timeline.log
export PYTHONUNBUFFERED=1 PYTHONUTF8=1
ts() { date '+%Y-%m-%d %H:%M:%S'; }

if [ -e revision/runs/model_D_s_base ]; then
    echo "[ABORT] revision/runs/model_D_s_base already exists" | tee -a $TL; exit 1
fi

echo "[C-resume] start $(ts) workers=4" >> $TL
"$PY" revision/scripts/resume_train.py --last 'revision\runs\model_C_n_robust\weights\last.pt' --workers 4 \
    --save-best-as 'revision\weights\model_C_n_robust.pt' > revision/logs/train_C_resume.log 2>&1
RC_C=$?
echo "[C-resume] end   $(ts) exit=$RC_C" >> $TL

echo "[D] start $(ts) workers=4" >> $TL
"$PY" 01_train_usecase_A_fast.py --data 'revision\data\Defense_AI_4cls\data.yaml' --model yolo11s.pt \
    --project "$PROJECT" --name model_D_s_base --workers 4 --save-best-as 'revision\weights\model_D_s_base.pt' \
    --device 0 > revision/logs/train_D.log 2>&1
RC_D=$?
echo "[D] end   $(ts) exit=$RC_D" >> $TL
echo "[ALL] done C_resume=$RC_C D=$RC_D" >> $TL
exit $(( RC_C != 0 || RC_D != 0 ))

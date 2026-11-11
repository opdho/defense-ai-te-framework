@echo off
REM ==========================================================================
REM  E4 retrain on the experiment machine, workers 4, single uninterrupted run each:
REM    A_rep   (01 script, yolo11n, reconstructed 4-class data.yaml)
REM    C_clean (02 script, yolo11n, data_model_B_local.yaml)
REM    B_rep   (02 script, yolo11s, data_model_B_local.yaml)
REM  Order: A_rep -> C_clean -> B_rep (shortest first). D is not retrained
REM  (revision\weights\model_D_s_base.pt was already trained here with workers 4 in one run).
REM  All other settings are the original script defaults (epochs, patience, lr0, augmentation,
REM  batch 16, imgsz 640, seed 42); only --workers 4 is added.
REM  Env    : test5_revision (ultralytics 8.4.21, torch 2.14.1+cu130)
REM  Run from the project folder. Project is ABSOLUTE so Ultralytics does not nest it under runs\detect\ .
REM  Start/end/exit code of each step -> revision\logs\E4_retrain_timeline.log
REM ==========================================================================
setlocal
if not defined PY set PY=python
set ROOT=%CD%
set PROJECT=%ROOT%\revision\runs
set TL=%ROOT%\revision\logs\E4_retrain_timeline.log
set PYTHONUNBUFFERED=1
set PYTHONUTF8=1

cd /d %ROOT%
if not exist revision\logs mkdir revision\logs
if not exist revision\weights mkdir revision\weights
if not exist %PROJECT% mkdir %PROJECT%

REM Abort if any run folder already exists (Ultralytics would silently create name2 and the copy below would pick the old run)
for %%N in (model_A_rep model_C_clean model_B_rep) do (
    if exist %PROJECT%\%%N (
        echo [ABORT] %PROJECT%\%%N already exists >> %TL%
        echo [ABORT] %PROJECT%\%%N already exists
        exit /b 1
    )
)

REM ---------------- A_rep: yolo11n + base recipe (01 script) ----------------
echo [A_rep] start %date% %time% workers=4 >> %TL%
"%PY%" 01_train_usecase_A_fast.py --data revision\data\Defense_AI_4cls\data.yaml --model yolo11n.pt --project %PROJECT% --name model_A_rep --workers 4 --save-best-as revision\weights\model_A_rep.pt --device 0 > revision\logs\train_A_rep.log 2>&1
set RC_A=%errorlevel%
echo [A_rep] end   %date% %time% exit=%RC_A% >> %TL%
if exist %PROJECT%\model_A_rep\weights\best.pt (
    copy /Y %PROJECT%\model_A_rep\weights\best.pt revision\weights\model_A_rep.pt
    echo [A_rep] best.pt copied to revision\weights\model_A_rep.pt >> %TL%
) else (
    echo [A_rep] best.pt NOT FOUND: %PROJECT%\model_A_rep\weights\best.pt >> %TL%
)

REM ---------------- C_clean: yolo11n + robust recipe (02 script) ------------
echo [C_clean] start %date% %time% workers=4 >> %TL%
"%PY%" 02_train_usecase_B_fast.py --data revision\data\data_model_B_local.yaml --model yolo11n.pt --project %PROJECT% --name model_C_clean --workers 4 --save-best-as revision\weights\model_C_clean.pt --device 0 > revision\logs\train_C_clean.log 2>&1
set RC_C=%errorlevel%
echo [C_clean] end   %date% %time% exit=%RC_C% >> %TL%
if exist %PROJECT%\model_C_clean\weights\best.pt (
    copy /Y %PROJECT%\model_C_clean\weights\best.pt revision\weights\model_C_clean.pt
    echo [C_clean] best.pt copied to revision\weights\model_C_clean.pt >> %TL%
) else (
    echo [C_clean] best.pt NOT FOUND: %PROJECT%\model_C_clean\weights\best.pt >> %TL%
)

REM ---------------- B_rep: yolo11s + robust recipe (02 script) --------------
echo [B_rep] start %date% %time% workers=4 >> %TL%
"%PY%" 02_train_usecase_B_fast.py --data revision\data\data_model_B_local.yaml --model yolo11s.pt --project %PROJECT% --name model_B_rep --workers 4 --save-best-as revision\weights\model_B_rep.pt --device 0 > revision\logs\train_B_rep.log 2>&1
set RC_B=%errorlevel%
echo [B_rep] end   %date% %time% exit=%RC_B% >> %TL%
if exist %PROJECT%\model_B_rep\weights\best.pt (
    copy /Y %PROJECT%\model_B_rep\weights\best.pt revision\weights\model_B_rep.pt
    echo [B_rep] best.pt copied to revision\weights\model_B_rep.pt >> %TL%
) else (
    echo [B_rep] best.pt NOT FOUND: %PROJECT%\model_B_rep\weights\best.pt >> %TL%
)

echo [ALL] done A_rep=%RC_A% C_clean=%RC_C% B_rep=%RC_B% >> %TL%
endlocal

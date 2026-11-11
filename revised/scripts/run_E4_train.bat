@echo off
REM ==========================================================================
REM  E4 2x2 training: C (yolo11n + robust recipe) -> D (yolo11s + base recipe)
REM  Env    : test5_revision (ultralytics 8.4.21, torch 2.14.1+cu130)
REM  Recipe : C = 02_train_usecase_B_fast.py defaults (epochs 70, patience 20, lr0 0.008, strong aug)
REM           D = 01_train_usecase_A_fast.py defaults (epochs 45, patience 15, lr0 0.01,  weak aug)
REM  Project is ABSOLUTE so Ultralytics does not nest it under runs\detect\ .
REM  Start/end/exit code of each step -> revision\logs\E4_train_timeline.log
REM ==========================================================================
setlocal
set PY=D:\miniconda3\envs\test5_revision\python.exe
set ROOT=D:\park\test5
set PROJECT=D:\park\test5\revision\runs
set TL=%ROOT%\revision\logs\E4_train_timeline.log
set PYTHONUNBUFFERED=1
set PYTHONUTF8=1

cd /d %ROOT%
if not exist revision\logs mkdir revision\logs
if not exist revision\weights mkdir revision\weights
if not exist %PROJECT% mkdir %PROJECT%

REM Abort if a run folder already exists (Ultralytics would silently create model_X2 and the copy below would pick the old run)
if exist %PROJECT%\model_C_n_robust (
    echo [ABORT] %PROJECT%\model_C_n_robust already exists >> %TL%
    echo [ABORT] %PROJECT%\model_C_n_robust already exists
    exit /b 1
)
if exist %PROJECT%\model_D_s_base (
    echo [ABORT] %PROJECT%\model_D_s_base already exists >> %TL%
    echo [ABORT] %PROJECT%\model_D_s_base already exists
    exit /b 1
)

REM ---------------- C: yolo11n + robust recipe (02 script) ----------------
echo [C] start %date% %time% >> %TL%
"%PY%" 02_train_usecase_B_fast.py --data revision\data\data_model_B_local.yaml --model yolo11n.pt --project %PROJECT% --name model_C_n_robust --save-best-as revision\weights\model_C_n_robust.pt --device 0 > revision\logs\train_C.log 2>&1
set RC_C=%errorlevel%
echo [C] end   %date% %time% exit=%RC_C% >> %TL%
if exist %PROJECT%\model_C_n_robust\weights\best.pt (
    copy /Y %PROJECT%\model_C_n_robust\weights\best.pt revision\weights\model_C_n_robust.pt
    echo [C] best.pt copied to revision\weights\model_C_n_robust.pt >> %TL%
) else (
    echo [C] best.pt NOT FOUND: %PROJECT%\model_C_n_robust\weights\best.pt >> %TL%
)

REM ---------------- D: yolo11s + base recipe (01 script) ------------------
echo [D] start %date% %time% >> %TL%
"%PY%" 01_train_usecase_A_fast.py --data revision\data\Defense_AI_4cls\data.yaml --model yolo11s.pt --project %PROJECT% --name model_D_s_base --save-best-as revision\weights\model_D_s_base.pt --device 0 > revision\logs\train_D.log 2>&1
set RC_D=%errorlevel%
echo [D] end   %date% %time% exit=%RC_D% >> %TL%
if exist %PROJECT%\model_D_s_base\weights\best.pt (
    copy /Y %PROJECT%\model_D_s_base\weights\best.pt revision\weights\model_D_s_base.pt
    echo [D] best.pt copied to revision\weights\model_D_s_base.pt >> %TL%
) else (
    echo [D] best.pt NOT FOUND: %PROJECT%\model_D_s_base\weights\best.pt >> %TL%
)

echo [ALL] done C=%RC_C% D=%RC_D% >> %TL%
endlocal

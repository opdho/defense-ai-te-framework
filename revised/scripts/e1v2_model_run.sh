#!/bin/bash
# E1 v2 for one model: unload other models, run 07b (unchanged, only --model differs), and on the first load
# record `ollama ps` (PROCESSOR column) and nvidia-smi memory.
# usage: e1v2_model_run.sh <model> <runs> <outdir> <logname>
cd /d/park/test5
MODEL=$1; RUNS=$2; OUT=$3; LOG=revision/logs/$4.log; PS=revision/logs/$4_ollama_ps.txt
PY=/d/miniconda3/envs/test5_revision/python.exe
export PYTHONUTF8=1 PYTHONUNBUFFERED=1
for m in $(ollama ps | awk 'NR>1{print $1}'); do ollama stop $m; done
sleep 3
{ echo "# before load $(date '+%F %T')"; nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader; } > $PS
"$PY" revision/07b_llm_scenario_trials_v2.py scenarios --model "$MODEL" --runs "$RUNS" --outdir "$OUT" > $LOG 2>&1 &
PID=$!
for i in $(seq 1 120); do
  if ollama ps | grep -q "^$MODEL "; then
    sleep 5
    { echo "# after first load $(date '+%F %T')"; ollama ps; nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader;
      nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader; } >> $PS
    break
  fi
  sleep 2
done
wait $PID
RC=$?
{ echo "# end $(date '+%F %T') exit=$RC"; ollama ps; } >> $PS
exit $RC

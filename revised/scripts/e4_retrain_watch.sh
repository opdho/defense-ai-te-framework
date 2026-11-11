#!/bin/bash
# Watch the E4 retrain (run_E4_retrain.bat / run_E4_retrain_from.bat) every 60 s, reading logs only.
# Exits (one line on stdout = reason) when one of:
#   (a) timeline has "[ALL] done"
#   (b) current training log has Traceback / out of memory / CUDA error
#   (c) current training log not updated for > 15 min
#   (d) available RAM < 2 GB
# usage: bash revision/scripts/e4_retrain_watch.sh [--once]
cd "${PROJECT_ROOT:-.}" || exit 1
TL=revision/logs/E4_retrain_timeline.log
ONCE=$1
STATUS=revision/logs/E4_retrain_watch_status.log

while true; do
  now=$(date +%s)
  avail_kb=$(awk '/MemAvailable/{print $2}' /proc/meminfo 2>/dev/null)
  [ -z "$avail_kb" ] && avail_kb=$(awk '/MemFree/{print $2}' /proc/meminfo)
  cur=""; log=""
  if [ -f $TL ]; then
    cur=$(grep -oE '^\[(A_rep|C_clean|B_rep)\] start' $TL | tail -n 1 | sed -E 's/^\[(.*)\] start/\1/')
  fi
  [ -n "$cur" ] && log=revision/logs/train_${cur}.log
  age=-1; epochs=""
  if [ -n "$log" ] && [ -f "$log" ]; then
    age=$(( now - $(stat -c %Y "$log") ))
    epochs=$(tr '\r' '\n' < "$log" | grep -aoE '^ *[0-9]+/[0-9]+ ' | tail -n 1 | tr -d ' ')
  fi
  echo "$(date '+%F %T') model=${cur:-none} log_age_s=$age epoch=${epochs:-?} avail_MB=$((avail_kb/1024))" >> $STATUS

  if [ -f $TL ] && grep -q '^\[ALL\] done' $TL; then echo "(a) ALL_DONE: $(grep '^\[ALL\] done' $TL | tail -n 1)"; exit 0; fi
  if [ -n "$log" ] && [ -f "$log" ]; then
    e=$(grep -aE 'Traceback|out of memory|CUDA error' "$log" | head -n 1 | cut -c1-200)
    if [ -n "$e" ]; then echo "(b) ERROR in $log: $e"; exit 10; fi
    if [ $age -gt 900 ]; then echo "(c) STALL: $log not updated for ${age}s (epoch ${epochs:-?})"; exit 11; fi
  fi
  if [ $((avail_kb/1024)) -lt 2048 ]; then echo "(d) LOW_RAM: available ${avail_kb} kB (model=${cur:-none})"; exit 12; fi

  if [ "$ONCE" = "--once" ]; then echo "ONCE_OK model=${cur:-none} log_age_s=$age avail_MB=$((avail_kb/1024))"; exit 0; fi
  sleep 60
done

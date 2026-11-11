#!/bin/bash
# usage: run.sh "<command>"  -> runs in D:/park/test5, appends row to revision/COMMANDS_RUN.md
cd /d/park/test5
S=$(date '+%Y-%m-%d %H:%M:%S')
bash -c "$1"
RC=$?
E=$(date '+%Y-%m-%d %H:%M:%S')
N=$(( $(grep -c '^| [0-9]' revision/COMMANDS_RUN.md) + 1 ))
CMD=$(printf '%s' "$1" | tr '\n' ' ' | sed 's/|/\|/g')
echo "| $N | $S | $E | $RC | \`$CMD\` | |" >> revision/COMMANDS_RUN.md
exit $RC

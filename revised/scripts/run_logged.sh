#!/bin/bash
# usage: run_logged.sh "<command>"  -> runs in the project folder, appends a row to revision/RUN_COMMANDS.md
cd "${PROJECT_ROOT:-.}" || exit 1
S=$(date '+%Y-%m-%d %H:%M:%S')
bash -c "$1"
RC=$?
E=$(date '+%Y-%m-%d %H:%M:%S')
N=$(( $(grep -c '^| [0-9]' revision/RUN_COMMANDS.md) + 1 ))
CMD=$(printf '%s' "$1" | tr '\n' ' ' | sed 's/|/\|/g')
echo "| $N | $S | $E | $RC | \`$CMD\` |" >> revision/RUN_COMMANDS.md
exit $RC

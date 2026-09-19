#!/bin/bash
# Runs the remaining campaign only inside a nightly window, then hard-stops so the machine cools.
# Every arm is resumable, so each night picks up exactly where the previous one was cut.
cd "$(dirname "$0")"
START_H=${START_H:-23}; HOURS=${HOURS:-5}
while ! grep -q ALL_COMPLETE runs/run_all.log 2>/dev/null; do
  now=$(date +%s); start=$(date -v${START_H}H -v0M -v0S +%s); [ $start -le $now ] && start=$((start+86400))
  echo "next window $(date -r $start '+%a %d %b %H:%M') for ${HOURS}h" >> runs/nightly.log
  sleep $((start-now))
  echo "window open $(date '+%a %H:%M')" >> runs/nightly.log
  timeout ${HOURS}h caffeinate -i ./run_all.sh >> runs/run_all.log 2>&1
  pkill -f llama-server; pkill -f run_model.sh; pkill -f gsm8k_gen
  echo "window closed $(date '+%a %H:%M')" >> runs/nightly.log
done
echo "campaign complete $(date)" >> runs/nightly.log

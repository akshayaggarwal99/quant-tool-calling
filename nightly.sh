#!/bin/bash
# One bounded window: run the campaign for HOURS, then hard-stop so the machine cools.
# Invoked by launchd at 23:00 (see ~/Library/LaunchAgents/com.akshay.quant-nightly.plist);
# every arm is resumable, so each night resumes where the last was cut.
cd "$(dirname "$0")"; HOURS=${HOURS:-5}
grep -q ALL_COMPLETE runs/run_all.log 2>/dev/null && { echo "campaign complete, nothing to do $(date)" >> runs/nightly.log; exit 0; }
echo "window open $(date '+%a %d %b %H:%M')" >> runs/nightly.log
timeout ${HOURS}h caffeinate -i ./run_all.sh >> runs/run_all.log 2>&1
pkill -f llama-server; pkill -f run_model.sh; pkill -f gsm8k_gen
echo "window closed $(date '+%a %d %b %H:%M')" >> runs/nightly.log

#!/bin/bash
# One bounded window: run the campaign until HOURS have elapsed OR the wall clock reaches STOP_AT
# (default 07:30), whichever comes first, then hard-stop so the machine cools before the day starts.
export PATH="/opt/homebrew/bin:/opt/homebrew/opt/coreutils/libexec/gnubin:/usr/local/bin:$PATH"
# Invoked by launchd at 02:00 (see ~/Library/LaunchAgents/com.akshay.quant-nightly.plist).
# Every arm is resumable, so each night resumes where the last was cut.
# 26 Sep lessons: (1) `caffeinate -i` only blocks idle sleep; from a dark wake the Mac sleeps again
# in two minutes, so the whole night ran in 2-minute slivers. `-s` holds the system awake on AC.
# (2) `gtimeout 5h` does not count time spent asleep, so the window overran into the morning. The
# watchdog below compares real clock time, and STOP_AT is an absolute cutoff regardless of start.
cd "$(dirname "$0")"; HOURS=${HOURS:-5}; STOP_AT=${STOP_AT:-07:30}
CAMPAIGN=${CAMPAIGN:-./run_llama.sh}; LOG=${LOG:-runs/llama.log}; MARK=${MARK:-LLAMA_COMPLETE}
grep -q "$MARK" "$LOG" 2>/dev/null && { echo "campaign complete, nothing to do $(date)" >> runs/nightly.log; exit 0; }
echo "window open $(date '+%a %d %b %H:%M')" >> runs/nightly.log
START=$(date +%s); END_H=$((START + HOURS*3600))
END_C=$(date -j -f '%Y-%m-%d %H:%M' "$(date '+%Y-%m-%d') $STOP_AT" +%s 2>/dev/null || echo $END_H)
[ "$END_C" -lt "$START" ] && END_C=$END_H            # STOP_AT already passed today: fall back to HOURS
DEADLINE=$END_H; [ "$END_C" -lt "$DEADLINE" ] && DEADLINE=$END_C
caffeinate -i -s "$CAMPAIGN" >> "$LOG" 2>&1 &
JOB=$!
while kill -0 $JOB 2>/dev/null; do
  [ "$(date +%s)" -ge "$DEADLINE" ] && { echo "deadline $(date '+%H:%M'), stopping" >> runs/nightly.log; kill $JOB 2>/dev/null; break; }
  sleep 60
done
wait $JOB 2>/dev/null
pkill -f "llama-server -m models/" 2>/dev/null; pkill -f "run_model.sh" 2>/dev/null; pkill -f "run_gsm8k_model.sh" 2>/dev/null; pkill -f "run_llama.sh" 2>/dev/null; pkill -f "gsm8k_gen.py" 2>/dev/null
echo "window closed $(date '+%a %d %b %H:%M')" >> runs/nightly.log

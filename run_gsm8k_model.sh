#!/bin/bash
# run_gsm8k_model.sh <gguf-stem> <server-alias> <rungs...>
# Free-form control for a second model family: same gsm8k_400.jsonl, same prompt, same 4,096 budget,
# same server flags as run_gsm8k.sh. Output runs/<stem>/gsm8k/<rung>.jsonl, resumable per row.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
STEM=$1; ALIAS=$2; shift 2; RUNGS="$*"; PORT=8099
mkdir -p "runs/$STEM/gsm8k"
for Q in $RUNGS; do
  OUT="runs/$STEM/gsm8k/$Q.jsonl"
  [ -s "$OUT" ] && [ "$(wc -l < "$OUT")" -ge 400 ] && { echo "[$STEM gsm8k $Q] done already"; continue; }
  [ -f "models/$STEM-$Q.gguf" ] || { echo "[$STEM gsm8k $Q] missing models/$STEM-$Q.gguf"; continue; }
  llama-server -m "models/$STEM-$Q.gguf" --alias "$ALIAS" --port $PORT -c 32768 -ngl 99 --jinja \
      > "runs/$STEM/gsm8k/$Q.server.log" 2>&1 &
  SRV=$!; for i in $(seq 1 90); do curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1 && break; sleep 2; done
  echo "[$STEM gsm8k $Q] generating x400 $(date +%H:%M)"
  GSM_MODEL="$ALIAS" .venv/bin/python gsm8k_gen.py $PORT "$OUT"
  kill $SRV 2>/dev/null; wait $SRV 2>/dev/null; echo "[$STEM gsm8k $Q] done $(date +%H:%M)"
done

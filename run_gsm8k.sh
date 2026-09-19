#!/bin/bash
# Same ladder, same server alias, free-form task. Only the weights change between rungs.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"; mkdir -p runs/gsm8k
PORT=8099
for Q in Q8_0 Q6_K Q5_K_M Q4_K_M Q3_K_M; do
  OUT="runs/gsm8k/$Q.jsonl"
  [ -s "$OUT" ] && [ "$(wc -l < "$OUT")" -ge 400 ] && { echo "[$Q] done already"; continue; }
  llama-server -m "models/Qwen3-1.7B-$Q.gguf" --alias "Qwen/Qwen3-1.7B" --port $PORT \
               -c 32768 -ngl 99 --jinja > "runs/gsm8k/$Q.server.log" 2>&1 &
  SRV=$!
  for i in $(seq 1 60); do curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1 && break; sleep 2; done
  echo "[$Q] generating GSM8K x400"
  .venv/bin/python gsm8k_gen.py $PORT "$OUT"
  kill $SRV 2>/dev/null; wait $SRV 2>/dev/null
  echo "[$Q] done"
done
echo GSM8K_COMPLETE

#!/bin/bash
set -u; cd "$(dirname "$0")"
until grep -q GSM8K_COMPLETE runs/gsm8k.log 2>/dev/null; do sleep 120; done
echo "queue start $(date)"
SUBSET=1 ./run_model.sh qwen3:8b-fp16  "Qwen/Qwen3-8B-FC"  Qwen3-8B  Q8_0 Q4_K_M Q3_K_M
./run_h4.sh
SUBSET=1 ./run_model.sh qwen3:14b-fp16 "Qwen/Qwen3-14B-FC" Qwen3-14B Q8_0 Q4_K_M Q3_K_M
echo QUEUE_COMPLETE

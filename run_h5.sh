#!/bin/bash
# H5: multi-turn amplification. BFCL multi_turn_base on Qwen3-1.7B at three rungs, after the queue.
set -u; cd "$(dirname "$0")"
until grep -q QUEUE_COMPLETE runs/queue.log 2>/dev/null; do sleep 300; done
CATEGORY=multi_turn_base ./run_model.sh qwen3:1.7b-fp16 "Qwen/Qwen3-1.7B-FC" Qwen3-1.7B Q8_0 Q4_K_M Q3_K_M
echo H5_COMPLETE

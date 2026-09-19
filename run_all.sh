#!/bin/bash
# Full remaining campaign in priority order. Every step is resumable and skips finished cells.
set -u; cd "$(dirname "$0")"
echo "run_all start $(date)"
./run_gsm8k.sh >> runs/gsm8k.log 2>&1                                                                       # H1/H3, ~8.5 h
./run_h4.sh >> runs/h4.log 2>&1                                                                          # H4, ~3 h
SUBSET=1 ./run_model.sh qwen3:8b-fp16  "Qwen/Qwen3-8B-FC"  Qwen3-8B  Q8_0 Q4_K_M Q3_K_M >> runs/queue.log 2>&1   # size, ~12 h
CATEGORY=multi_turn_base ./run_model.sh qwen3:1.7b-fp16 "Qwen/Qwen3-1.7B-FC" Qwen3-1.7B Q8_0 Q4_K_M Q3_K_M >> runs/h5.log 2>&1  # H5, ~6 h
echo QUEUE_COMPLETE >> runs/queue.log; echo H5_COMPLETE >> runs/h5.log
SUBSET=1 ./run_model.sh qwen3:14b-fp16 "Qwen/Qwen3-14B-FC" Qwen3-14B Q8_0 Q4_K_M Q3_K_M >> runs/queue.log 2>&1  # size, ~20 h
echo ALL_COMPLETE; echo "run_all end $(date)"

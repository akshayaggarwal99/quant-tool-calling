#!/bin/bash
# Second model family for the TMLR version (added 25 Sep 2026). Same protocol as the Qwen3 arms:
# three rungs from one FP16 source, BFCL simple_python n=200 (subset200.json, as Qwen3-8B/14B),
# then GSM8K x400 with the 4,096 budget. The meta-llama HF repos are gated, so BFCL loads the
# tokenizer/config from the ungated unsloth mirrors (same files) via REMOTE_OPENAI_TOKENIZER_PATH. Llama-3.2-3B first (cheap, and the size band where the
# 1.7B cliff lives), then Llama-3.1-8B (the model Kurt 2026 used). Every step resumable.
set -u; cd "$(dirname "$0")"
echo "run_llama start $(date)"
REMOTE_OPENAI_BASE_URL=http://localhost:8099/v1 REMOTE_OPENAI_TOKENIZER_PATH=unsloth/Llama-3.2-3B-Instruct SUBSET=1 ./run_model.sh llama3.2:3b-instruct-fp16 "meta-llama/Llama-3.2-3B-Instruct-FC" Llama-3.2-3B Q8_0 Q4_K_M Q3_K_M
# smoke gate: the first rung must have produced a score file, otherwise stop and do not burn the window
S=$(ls runs/Llama-3.2-3B/Q8_0/score/*/*/*simple_python*score.json 2>/dev/null | head -1)
[ -n "$S" ] || { echo "SMOKE_FAIL: no score file for Llama-3.2-3B Q8_0; see runs/Llama-3.2-3B/simple_python-Q8_0.bfcl.log"; exit 1; }
./run_gsm8k_model.sh Llama-3.2-3B "meta-llama/Llama-3.2-3B-Instruct" Q8_0 Q4_K_M Q3_K_M
REMOTE_OPENAI_BASE_URL=http://localhost:8099/v1 REMOTE_OPENAI_TOKENIZER_PATH=unsloth/Llama-3.1-8B-Instruct SUBSET=1 ./run_model.sh llama3.1:8b-instruct-fp16 "meta-llama/Llama-3.1-8B-Instruct-FC" Llama-3.1-8B Q8_0 Q4_K_M Q3_K_M
./run_gsm8k_model.sh Llama-3.1-8B "meta-llama/Llama-3.1-8B-Instruct" Q8_0 Q4_K_M Q3_K_M
echo LLAMA_COMPLETE; echo "run_llama end $(date)"

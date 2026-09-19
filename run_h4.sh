#!/bin/bash
# H4: does a logit penalty on overthinking markers preserve schema compliance?
# Tokens are Qwen3 ids for ' wait',' Wait',' but',' But',' alternatively',' Alternatively',' hmm',' Hmm'.
# Fixed penalty of -2.0 on each; an approximation of Lotfi et al.'s fixed-lambda penalty, stated as such.
set -u; cd "$(dirname "$0")"
PEN=""; for t in 3783 13824 714 1988 68387 38478 87501 88190; do PEN="$PEN --logit-bias ${t}-2.0"; done
for Q in Q4_K_M Q3_K_M; do
  [ -d "runs/h4/$Q/score" ] && continue
  mkdir -p runs/h4 models; ln -sf "$PWD/models/Qwen3-1.7B-$Q.gguf" "models/h4-$Q.gguf"
  EXTRA_SERVER_FLAGS="$PEN" ./run_model.sh qwen3:1.7b-fp16 "Qwen/Qwen3-1.7B-FC" h4 $Q
done
echo H4_COMPLETE

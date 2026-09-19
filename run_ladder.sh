#!/bin/bash
# Run BFCL across a controlled quantization ladder built from one FP16 source.
# Each rung is served by llama-server under the model name BFCL sends, so the
# only thing that changes between runs is the weights.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
MODEL_ALIAS="Qwen/Qwen3-1.7B"        # name BFCL sends to the endpoint
BFCL_MODEL="Qwen/Qwen3-1.7B-FC"      # BFCL model config id
PORT=8099
CATS="${CATS:-simple_python}"
LADDER="${LADDER:-Q8_0 Q6_K Q5_K_M Q4_K_M Q3_K_M}"

export BFCL_PROJECT_ROOT="$HERE/bfcl_root"
export LOCAL_SERVER_ENDPOINT=localhost
export LOCAL_SERVER_PORT=$PORT
mkdir -p "$BFCL_PROJECT_ROOT" "$HERE/runs"

for Q in $LADDER; do
  GGUF="$HERE/models/Qwen3-1.7B-$Q.gguf"
  DEST="$HERE/runs/$Q"
  if [ -d "$DEST/score" ]; then echo "[$Q] already done, skipping"; continue; fi
  [ -f "$GGUF" ] || { echo "[$Q] missing $GGUF"; continue; }

  echo "[$Q] serving $(basename "$GGUF")"
  llama-server -m "$GGUF" --alias "$MODEL_ALIAS" --port $PORT \
               -c 8192 -ngl 99 --jinja > "$HERE/runs/$Q.server.log" 2>&1 &
  SRV=$!
  for i in $(seq 1 60); do
    curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1 && break
    sleep 2
  done
  if ! curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1; then
    echo "[$Q] server failed to start, see runs/$Q.server.log"; kill $SRV 2>/dev/null; continue
  fi

  rm -rf "$BFCL_PROJECT_ROOT/result" "$BFCL_PROJECT_ROOT/score"
  echo "[$Q] generating: $CATS"
  "$HERE/.venv/bin/bfcl" generate --model "$BFCL_MODEL" --test-category $CATS \
        --skip-server-setup --num-threads 4 >> "$HERE/runs/$Q.bfcl.log" 2>&1
  echo "[$Q] evaluating"
  "$HERE/.venv/bin/bfcl" evaluate --model "$BFCL_MODEL" --test-category $CATS \
        --partial-eval >> "$HERE/runs/$Q.bfcl.log" 2>&1

  mkdir -p "$DEST"
  cp -R "$BFCL_PROJECT_ROOT/result" "$BFCL_PROJECT_ROOT/score" "$DEST"/ 2>/dev/null
  kill $SRV 2>/dev/null; wait $SRV 2>/dev/null
  echo "[$Q] done -> runs/$Q"
done
echo "LADDER_COMPLETE"

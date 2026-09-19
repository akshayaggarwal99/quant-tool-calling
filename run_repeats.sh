#!/bin/bash
# Run-to-run variance control. Re-runs two rungs already measured, so the
# spread across the ladder can be compared against the spread of one rung
# against itself. Without this the ladder differences are uninterpretable.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
until grep -q LADDER_COMPLETE runs/ladder.log 2>/dev/null; do sleep 60; done
echo "ladder finished, starting repeats"
MODEL_ALIAS="Qwen/Qwen3-1.7B"; BFCL_MODEL="Qwen/Qwen3-1.7B-FC"; PORT=8099
export BFCL_PROJECT_ROOT="$HERE/bfcl_root" LOCAL_SERVER_ENDPOINT=localhost LOCAL_SERVER_PORT=$PORT
for REP in r2 r3; do
  for Q in Q8_0 Q4_K_M; do
    DEST="$HERE/runs/${Q}-${REP}"
    [ -d "$DEST/score" ] && continue
    GGUF="$HERE/models/Qwen3-1.7B-$Q.gguf"
    llama-server -m "$GGUF" --alias "$MODEL_ALIAS" --port $PORT -c 8192 -ngl 99 --jinja \
                 > "$HERE/runs/${Q}-${REP}.server.log" 2>&1 &
    SRV=$!
    for i in $(seq 1 60); do curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1 && break; sleep 2; done
    rm -rf "$BFCL_PROJECT_ROOT/result" "$BFCL_PROJECT_ROOT/score"
    "$HERE/.venv/bin/bfcl" generate --model "$BFCL_MODEL" --test-category simple_python \
          --skip-server-setup --num-threads 4 >> "$HERE/runs/${Q}-${REP}.bfcl.log" 2>&1
    "$HERE/.venv/bin/bfcl" evaluate --model "$BFCL_MODEL" --test-category simple_python \
          --partial-eval >> "$HERE/runs/${Q}-${REP}.bfcl.log" 2>&1
    mkdir -p "$DEST"; cp -R "$BFCL_PROJECT_ROOT/result" "$BFCL_PROJECT_ROOT/score" "$DEST"/ 2>/dev/null
    kill $SRV 2>/dev/null; wait $SRV 2>/dev/null
    echo "[$Q $REP] done"
  done
done
echo REPEATS_COMPLETE

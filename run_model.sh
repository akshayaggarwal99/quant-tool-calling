#!/bin/bash
# run_model.sh <ollama-fp16-tag> <bfcl-model-id> <gguf-stem> <rungs...>
# Builds the rungs from the Ollama FP16 blob if missing, serves each under the alias BFCL sends,
# runs BFCL simple_python (n=400, or n=200 if SUBSET=1) and archives to runs/<stem>/<rung>/.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
TAG=$1; BFCL_MODEL=$2; STEM=$3; shift 3; RUNGS="$*"
ALIAS="${BFCL_MODEL%-FC}"; PORT=8099; CAT="${CATEGORY:-simple_python}"
curl -sf http://localhost:11434/ >/dev/null 2>&1 || { nohup ollama serve >/dev/null 2>&1 & sleep 5; }   # launchd runs without the Ollama app
ollama pull "$TAG" >/dev/null 2>&1
SRC=$(ollama show --modelfile "$TAG" 2>/dev/null | awk '/^FROM/{print $2; exit}')
[ -f "$SRC" ] || { echo "[$STEM] no FP16 blob for $TAG"; exit 1; }
for Q in $RUNGS; do [ -f "models/$STEM-$Q.gguf" ] || llama-quantize "$SRC" "models/$STEM-$Q.gguf" "$Q" >/dev/null 2>&1; done
export BFCL_PROJECT_ROOT="$HERE/bfcl_root_$STEM" LOCAL_SERVER_ENDPOINT=localhost LOCAL_SERVER_PORT=$PORT
mkdir -p "$BFCL_PROJECT_ROOT" "runs/$STEM"
[ "${SUBSET:-0}" = 1 ] && [ "$CAT" = simple_python ] && cp subset200.json "$BFCL_PROJECT_ROOT/test_case_ids_to_generate.json"
for Q in $RUNGS; do
  DEST="runs/$STEM/$Q"; [ "$CAT" != simple_python ] && DEST="runs/$STEM/$CAT/$Q"; mkdir -p "$(dirname "$DEST")"; [ -d "$DEST/score" ] && { echo "[$STEM $Q] done"; continue; }
  llama-server -m "models/$STEM-$Q.gguf" --alias "$ALIAS" --port $PORT -c 32768 -ngl 99 --jinja ${EXTRA_SERVER_FLAGS:-} > "runs/$STEM/$CAT-$Q.server.log" 2>&1 &
  SRV=$!; for i in $(seq 1 90); do curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1 && break; sleep 2; done
  rm -rf "$BFCL_PROJECT_ROOT/result" "$BFCL_PROJECT_ROOT/score"
  echo "[$STEM $Q] generating $(date +%H:%M)"
  GEN_FLAGS=""; [ "${SUBSET:-0}" = 1 ] && GEN_FLAGS="--run-ids"
  .venv/bin/bfcl generate --model "$BFCL_MODEL" --test-category $CAT --skip-server-setup --num-threads 4 $GEN_FLAGS >> "runs/$STEM/$CAT-$Q.bfcl.log" 2>&1
  .venv/bin/bfcl evaluate --model "$BFCL_MODEL" --test-category $CAT --partial-eval >> "runs/$STEM/$CAT-$Q.bfcl.log" 2>&1
  mkdir -p "$DEST"; cp -R "$BFCL_PROJECT_ROOT/result" "$BFCL_PROJECT_ROOT/score" "$DEST"/ 2>/dev/null
  kill $SRV 2>/dev/null; wait $SRV 2>/dev/null; echo "[$STEM $Q] done $(date +%H:%M)"
done

#!/bin/bash
# One-glance status of the quantization ladder run.
cd "$(dirname "$0")"
echo "=== rungs complete ==="
for q in Q8_0 Q6_K Q5_K_M Q4_K_M Q3_K_M; do
  if [ -d "runs/$q/score" ]; then
    acc=$(grep -oE 'Accuracy: [0-9.]+%' "runs/$q.bfcl.log" 2>/dev/null | tail -1)
    n=$(wc -l < runs/$q/result/*/non_live/*simple_python*.json 2>/dev/null | tr -d ' ')
    printf "  %-8s %-18s (%s entries)\n" "$q" "${acc:-no score}" "${n:-?}"
  else
    printf "  %-8s pending\n" "$q"
  fi
done
cur=$(tail -3 runs/ladder.log 2>/dev/null | grep -oE '\[Q[0-9A-Z_]+\]' | tail -1)
live=$(wc -l < bfcl_root/result/*/non_live/*simple_python*.json 2>/dev/null | tr -d ' ')
echo "=== in flight ==="
pgrep -f run_ladder.sh >/dev/null && echo "  running ${cur:-?}, ${live:-0}/400 entries" || echo "  ladder not running"
echo "=== our memory footprint ==="
ps -o rss= -p $(pgrep -f llama-server | head -1) 2>/dev/null | awk '{printf "  llama-server: %.1f GB\n", $1/1048576}'

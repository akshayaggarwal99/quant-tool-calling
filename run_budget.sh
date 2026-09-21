#!/bin/bash
# Re-run only the 213 Q3_K_M math generations that hit the 4,096 cap, with a 16,384 budget, on a
# second port so it can overlap the 14B arm. Answers: how much of the collapse is the budget.
set -u; cd "$(dirname "$0")"
mkdir -p runs/gsm8k_budget
[ -f runs/gsm8k_budget/Q3_K_M_16k.jsonl ] && [ "$(wc -l < runs/gsm8k_budget/Q3_K_M_16k.jsonl)" -ge 213 ] && { echo BUDGET_COMPLETE; exit 0; }
.venv/bin/python - <<'PY'
import json
rows=[json.loads(l) for l in open("runs/gsm8k/Q3_K_M.jsonl")]
tr=[{"id":r["id"],"gold":r["gold"]} for r in rows if r["finish_reason"]=="length"]
qs={json.loads(l)["id"]:json.loads(l) for l in open("gsm8k_400.jsonl")}
with open("runs/gsm8k_budget/truncated_ids.jsonl","w") as f:
    for t in tr: f.write(json.dumps(qs[t["id"]])+"\n")
print("truncated at Q3_K_M:", len(tr))
PY
sed -e 's/max_tokens=4096/max_tokens=16384/' -e 's#open("gsm8k_400.jsonl")#open("runs/gsm8k_budget/truncated_ids.jsonl")#' gsm8k_gen.py > gsm8k_gen_budget.py
llama-server -m models/Qwen3-1.7B-Q3_K_M.gguf --alias Qwen/Qwen3-1.7B --port 8100 -c 65536 -np 2 -ngl 99 --jinja > runs/gsm8k_budget/server.log 2>&1 &
SRV=$!; for i in $(seq 1 60); do curl -sf http://localhost:8100/v1/models >/dev/null 2>&1 && break; sleep 2; done
.venv/bin/python gsm8k_gen_budget.py 8100 runs/gsm8k_budget/Q3_K_M_16k.jsonl
kill $SRV 2>/dev/null; echo BUDGET_COMPLETE

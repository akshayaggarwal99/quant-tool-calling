#!/usr/bin/env python3
"""Free-form control arm: GSM8K through the same llama-server the BFCL runs used.
Logs every full generation so scoring under different extractors is a re-read, not a re-run."""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

PORT, OUT, MODEL = sys.argv[1], sys.argv[2], "Qwen/Qwen3-1.7B"
client = OpenAI(base_url=f"http://localhost:{PORT}/v1", api_key="x")
PROMPT = ("Solve the following math problem step by step. "
          "Finish with a line of the form 'The answer is N.' where N is a number.\n\n{q}")

def one(rec):
    t0 = time.time()
    r = client.chat.completions.create(model=MODEL, temperature=0.001, max_tokens=4096,
        messages=[{"role": "user", "content": PROMPT.format(q=rec["question"])}])
    m = r.choices[0].message
    return {"id": rec["id"], "gold": rec["gold"],
            "content": m.content or "",
            "reasoning": getattr(m, "reasoning", None) or getattr(m, "reasoning_content", None) or "",
            "completion_tokens": r.usage.completion_tokens if r.usage else None,
            "finish_reason": r.choices[0].finish_reason, "wall_s": round(time.time() - t0, 2)}

recs = [json.loads(l) for l in open("gsm8k_400.jsonl")]
with open(OUT, "w") as f, ThreadPoolExecutor(4) as ex:
    for i, res in enumerate(ex.map(one, recs), 1):
        f.write(json.dumps(res) + "\n"); f.flush()
        if i % 50 == 0: print(f"  {i}/400", flush=True)
print("done", OUT)

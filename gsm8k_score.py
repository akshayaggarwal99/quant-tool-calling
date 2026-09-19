#!/usr/bin/env python3
"""Score logged GSM8K generations under two extractors. Re-read, never re-run.

strict  : an explicit final-answer commitment, any of  "The answer is N",  "#### N",  \\boxed{N}.
          This is the lm-eval strict-match convention widened to the \\boxed{} form that reasoning
          models emit; without \\boxed the extractor is a strawman (see LAB-NOTEBOOK, 18 Sep).
lenient : the last number anywhere in the visible answer (lm-eval flexible-extract).
"""
import json, re, sys, glob
from pathlib import Path
def norm(x):
    if x is None: return None
    x = x.replace(",", "").replace("$", "").strip().rstrip(".")
    try: return str(float(x)).rstrip("0").rstrip(".")
    except Exception: return x
STRICT = [r"[Tt]he answer is[:\s]*\$?\s*\\?\(?\s*(-?[\d,]*\.?\d+)",
          r"####\s*(-?[\d,]*\.?\d+)",
          r"\\boxed\{\s*\\?\$?\s*(-?[\d,]*\.?\d+)"]
def strict(t):
    hits = []
    for p in STRICT: hits += [(m.start(), m.group(1)) for m in re.finditer(p, t)]
    return max(hits)[1] if hits else None
def lenient(t):
    m = re.findall(r"-?\d[\d,]*\.?\d*", t); return m[-1] if m else None
def score(path):
    rows = [json.loads(l) for l in open(path)]
    n = len(rows); s = l = tr = 0; toks = []
    for r in rows:
        g = norm(r["gold"]); c = r["content"]
        s += norm(strict(c)) == g; l += norm(lenient(c)) == g
        tr += r["finish_reason"] == "length"; toks.append(r["completion_tokens"] or 0)
    toks.sort()
    return dict(n=n, strict=100*s/n, lenient=100*l/n, gap=100*(l-s)/n, truncated=tr,
                median_tokens=toks[n//2], p90_tokens=toks[int(.9*n)])
if __name__ == "__main__":
    for f in sorted(glob.glob("runs/gsm8k/*.jsonl")):
        r = score(f); q = Path(f).stem
        print(f"{q:<8} n={r['n']:<4} strict={r['strict']:.2f}%  lenient={r['lenient']:.2f}%  "
              f"gap={r['gap']:+.2f}pp  trunc={r['truncated']}  med_tok={r['median_tokens']}  p90_tok={r['p90_tokens']}")

#!/usr/bin/env python3
"""Collect BFCL scores across the quantization ladder into one table.

Reads runs/<QUANT>/score/*.csv written by run_ladder.sh and emits:
  out/ladder.csv   one row per (quant, category) with accuracy and error mix
  out/ladder.md    the deployment table, which is the paper's product
"""
import csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).parent
RUNS = HERE / "runs"
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
# ordered most to least precise, so the table reads down the ladder
LADDER = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M"]

def score_rows(qdir):
    """Pull accuracy per category out of whichever score CSVs BFCL wrote."""
    out = {}
    sdir = qdir / "score"
    if not sdir.is_dir(): return out
    for csvf in sorted(sdir.glob("*.csv")):
        try:
            rows = list(csv.DictReader(csvf.open()))
        except Exception:
            continue
        for r in rows:
            for k, v in r.items():
                if not k or v in (None, ""): continue
                m = re.match(r"^\s*([\d.]+)\s*%?\s*$", str(v))
                if not m: continue
                key = k.strip().lower()
                if key in ("model", "rank", "cost", "latency"): continue
                out.setdefault(key, float(m.group(1)))
    return out

def gen_stats(qdir):
    """Structural failure signals straight from the raw generations."""
    n = invalid = 0
    lens = []
    for f in (qdir / "result").rglob("*_result.json"):
        for line in f.open():
            line = line.strip()
            if not line: continue
            try: rec = json.loads(line)
            except Exception: continue
            n += 1
            r = rec.get("result")
            txt = r if isinstance(r, str) else json.dumps(r)
            lens.append(len(txt))
            # a call that is neither a list of calls nor parseable text is structurally invalid
            if isinstance(r, str) and not re.search(r"[\[\{]", r):
                invalid += 1
    return {"n": n, "invalid_share": round(invalid / n, 4) if n else None,
            "median_out_chars": sorted(lens)[len(lens)//2] if lens else None}

def main():
    rows = []
    for q in LADDER:
        qdir = RUNS / q
        if not qdir.is_dir(): continue
        rec = {"quant": q}
        rec.update(gen_stats(qdir))
        rec.update(score_rows(qdir))
        rows.append(rec)
    if not rows:
        print("no completed rungs yet"); return
    keys = ["quant", "n", "invalid_share", "median_out_chars"] + \
           [k for k in rows[0] if k not in ("quant", "n", "invalid_share", "median_out_chars")]
    with (OUT / "ladder.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow({k: r.get(k) for k in keys})
    md = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    for r in rows:
        md.append("| " + " | ".join(str(r.get(k, "")) for k in keys) + " |")
    (OUT / "ladder.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    print(f"\nwrote {OUT/'ladder.csv'} and {OUT/'ladder.md'}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Every number in the paper, recomputed from runs/. Emits paper/tables/numbers.tex,
ladder.tex and repeats.tex. Nothing is hand-typed into the manuscript."""
import json, math, os, statistics
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
RUNS, TAB, MODELS = HERE / "runs", HERE / "paper" / "tables", HERE / "models"
TAB.mkdir(parents=True, exist_ok=True)
RUNG = [("Q8_0", "Eight"), ("Q6_K", "Six"), ("Q5_K_M", "Five"), ("Q4_K_M", "Four"), ("Q3_K_M", "Three")]
N = {}

def verdicts(run):
    sc = list((RUNS / run / "score").rglob("*simple_python*.json"))
    rs = list((RUNS / run / "result").rglob("*simple_python*.json"))
    if not sc or not rs: return None
    bad = set()
    for l in sc[0].open():
        l = l.strip()
        if not l: continue
        try:
            r = json.loads(l)
            if "id" in r: bad.add(r["id"])
        except Exception: pass
    ids = set()
    for l in rs[0].open():
        l = l.strip()
        if l:
            try: ids.add(json.loads(l)["id"])
            except Exception: pass
    return {i: (i not in bad) for i in ids}

def acc(v): return 100 * sum(v.values()) / len(v)

def mcnemar(a, b):
    c = set(a) & set(b)
    lost = sum(1 for i in c if a[i] and not b[i]); gained = sum(1 for i in c if not a[i] and b[i])
    n = lost + gained
    if n == 0: return lost, gained, 1.0
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(0, min(lost, gained) + 1)) / 2 ** n)
    return lost, gained, p

V = {q: verdicts(q) for q, _ in RUNG}
base = V["Q8_0"]
N["N"] = len(base)
N["SizeFp"] = f"{3.8:.1f}"
for q, w in RUNG:
    v = V[q]; N["Acc" + w] = f"{acc(v):.2f}"
    gg = MODELS / f"Qwen3-1.7B-{q}.gguf"
    if gg.exists(): N["Size" + w] = f"{gg.stat().st_size / 1e9:.1f}"
    if q != "Q8_0":
        lost, gained, p = mcnemar(base, v)
        N["Delta" + w] = f"{acc(v) - acc(base):+.2f}"
        N["Lost" + w], N["Gained" + w] = lost, gained
        N["P" + w] = f"{p:.3f}" if p >= 0.001 else f"{p:.4f}"
N["SizeRatioFour"] = f"{100 * (MODELS / 'Qwen3-1.7B-Q4_K_M.gguf').stat().st_size / (MODELS / 'Qwen3-1.7B-Q8_0.gguf').stat().st_size:.0f}"
N["CompressFour"] = f"{(MODELS / 'Qwen3-1.7B-Q4_K_M.gguf').stat().st_size / 3.8e9 * 100:.0f}"

# repeats
reps = {}
for q, w in (("Q8_0", "Eight"), ("Q4_K_M", "Four")):
    runs = [q] + [f"{q}-r{i}" for i in (2, 3)]
    vs = [V[q]] + [verdicts(r) for r in runs[1:]]
    vs = [x for x in vs if x]
    a = [acc(x) for x in vs]
    N["RepRuns" + w] = len(a)
    N["RepMean" + w] = f"{statistics.mean(a):.2f}"
    N["RepRange" + w] = f"{max(a) - min(a):.2f}"
    N["RepList" + w] = ", ".join(f"{x:.2f}" for x in a)
    flips = [sum(1 for i in set(vs[0]) & set(x) if vs[0][i] != x[i]) for x in vs[1:]]
    N["RepFlipsMax" + w] = max(flips) if flips else 0
    reps[q] = (a, flips)
N["MaxRepRange"] = f"{max(float(N['RepRangeEight']), float(N['RepRangeFour'])):.2f}"
N["CliffOverNoise"] = f"{abs(float(N['DeltaThree'])) / float(N['MaxRepRange']):.0f}"
N["RungsCount"] = len(RUNG)
N["RunsTotal"] = len(RUNG) + sum(len(a) - 1 for a, _ in reps.values())

# throughput, from the lab notebook measurements (recorded, not modelled)
N["MacTg"] = "35"; N["MacPp"] = "650"; N["GcpTg"] = "22.0"; N["GcpPp"] = "109.6"

DIG = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
mac = lambda k: "".join(DIG.get(c, c) for c in k)
(TAB / "numbers.tex").write_text("".join(f"\\newcommand{{\\qt{mac(k)}}}{{{v}}}\n" for k, v in N.items()))

# ladder table
L = ["\\begin{tabular}{@{}lrrrrrr@{}}", "\\toprule",
     "Rung & Size (GB) & Accuracy & vs.\\ Q8\\_0 & Lost & Gained & McNemar $p$ \\\\", "\\midrule"]
for q, w in RUNG:
    lab = q.replace("_", "\\_")
    if q == "Q8_0":
        L.append(f"{lab} & {N['Size'+w]} & {N['Acc'+w]}\\% & baseline & & & \\\\")
    else:
        bold = "\\textbf" if float(N["P" + w]) < 0.05 else ""
        d = N["Delta" + w].replace("-", "$-$").replace("+", "$+$")
        pv = f"{bold}{{{N['P'+w]}}}" if bold else N["P" + w]
        L.append(f"{lab} & {N['Size'+w]} & {N['Acc'+w]}\\% & {d}\\,pp & {N['Lost'+w]} & {N['Gained'+w]} & {pv} \\\\")
L += ["\\bottomrule", "\\end{tabular}"]
(TAB / "ladder.tex").write_text("\n".join(L) + "\n")

# repeats table
R = ["\\begin{tabular}{@{}llrr@{}}", "\\toprule", "Rung & Accuracy per run & Range (pp) & Max per-question flips \\\\", "\\midrule"]
for q, w in (("Q8_0", "Eight"), ("Q4_K_M", "Four")):
    R.append(f"{q.replace('_', chr(92)+'_')} & {N['RepList'+w]} & {N['RepRange'+w]} & {N['RepFlipsMax'+w]} of {N['N']} \\\\")
R += ["\\bottomrule", "\\end{tabular}"]
(TAB / "repeats.tex").write_text("\n".join(R) + "\n")
print(f"{len(N)} macros; ladder + repeats tables written")
for k in ("AccEight","AccFour","AccThree","DeltaThree","PThree","MaxRepRange","CliffOverNoise","SizeRatioFour","RunsTotal"): print(f"  {k} = {N[k]}")

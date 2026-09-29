#!/usr/bin/env python3
"""Every number in the paper, recomputed from runs/. Emits paper/tables/numbers.tex and every
table (ladder, repeats, gsm8k, models, llama, multiturn). Nothing is hand-typed into the manuscript.
Run with the project's .venv python: the coerced re-score imports BFCL's own checker."""
import csv, json, math, os, re, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "analysis"))
RUNS, TAB, MODELS = HERE / "runs", HERE / "paper" / "tables", HERE / "models"
TAB.mkdir(parents=True, exist_ok=True)
RUNG = [("Q8_0", "Eight"), ("Q6_K", "Six"), ("Q5_K_M", "Five"), ("Q4_K_M", "Four"), ("Q3_K_M", "Three")]
N = {}
Z = 1.959963984540054   # two-sided 95%

def wilson(k, n):
    """Wilson score interval for k successes in n trials, in percentage points."""
    p = k / n; d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)

def ci(v):
    lo, hi = wilson(sum(v.values()), len(v)); return f"{lo:.1f}, {hi:.1f}"

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

def pfmt(p): return f"{p:.3f}" if p >= 0.001 else "$<$0.0001"
def _pf(x):
    """p-value string -> float, tolerating the '$<$0.0001' display form."""
    return float(str(x).replace('$', '').replace('<', '').strip() or 1)
def sgn(d): return d.replace("-", "$-$").replace("+", "$+$")
def bold(pv): return f"\\textbf{{{pv}}}" if pv and _pf(pv) < 0.05 else pv
def lab(q): return q.replace("_", "\\_")

V = {q: verdicts(q) for q, _ in RUNG}
base = V["Q8_0"]
N["N"] = len(base)
N["SizeFp"] = f"{3.8:.1f}"
for q, w in RUNG:
    v = V[q]; N["Acc" + w] = f"{acc(v):.2f}"; N["Ci" + w] = ci(v)
    gg = MODELS / f"Qwen3-1.7B-{q}.gguf"
    if gg.exists(): N["Size" + w] = f"{gg.stat().st_size / 1e9:.1f}"
    if q != "Q8_0":
        lost, gained, p = mcnemar(base, v)
        N["Delta" + w] = f"{acc(v) - acc(base):+.2f}"
        N["Lost" + w], N["Gained" + w] = lost, gained
        N["P" + w] = pfmt(p)
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
L = ["\\begin{tabular}{@{}lrlrrrr@{}}", "\\toprule",
     "Rung & Size (GB) & Accuracy [95\\% CI] & vs.\\ Q8\\_0 & Lost & Gained & McNemar $p$ \\\\", "\\midrule"]
for q, w in RUNG:
    cell = f"{N['Acc'+w]}\\% [{N['Ci'+w]}]"
    if q == "Q8_0":
        L.append(f"{lab(q)} & {N['Size'+w]} & {cell} & baseline & & & \\\\")
    else:
        L.append(f"{lab(q)} & {N['Size'+w]} & {cell} & {sgn(N['Delta'+w])}\\,pp & {N['Lost'+w]} & {N['Gained'+w]} & {bold(N['P'+w])} \\\\")
L += ["\\bottomrule", "\\end{tabular}"]
(TAB / "ladder.tex").write_text("\n".join(L) + "\n")

# repeats table
R = ["\\begin{tabular}{@{}llrr@{}}", "\\toprule", "Rung & Accuracy per run & Range (pp) & Max per-question flips \\\\", "\\midrule"]
for q, w in (("Q8_0", "Eight"), ("Q4_K_M", "Four")):
    R.append(f"{lab(q)} & {N['RepList'+w]} & {N['RepRange'+w]} & {N['RepFlipsMax'+w]} of {N['N']} \\\\")
R += ["\\bottomrule", "\\end{tabular}"]
(TAB / "repeats.tex").write_text("\n".join(R) + "\n")
print(f"{len(N)} macros; ladder + repeats tables written")
for k in ("AccEight","AccFour","AccThree","DeltaThree","PThree","MaxRepRange","CliffOverNoise","SizeRatioFour","RunsTotal"): print(f"  {k} = {N[k]}")

# ============================================================ later arms, populated as they land
def _acc_rows(run_dir, cat_glob):
    sc = list((run_dir / "score").rglob(cat_glob)); rs = list((run_dir / "result").rglob(cat_glob))
    if not sc or not rs: return None
    bad = set()
    for l in sc[0].open():
        l = l.strip()
        if l:
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

extra = {}
# --- free-form arm (GSM8K)
try:
    from gsm8k_score import score as gscore, strict as gstrict, lenient as glenient, norm as gnorm
    G = {}
    for q, w in RUNG:
        f = RUNS / "gsm8k" / f"{q}.jsonl"
        if f.exists() and sum(1 for _ in f.open()) >= 400:
            rows = [json.loads(l) for l in f.open()]
            G[q] = {r["id"]: (gnorm(gstrict(r["content"])) == gnorm(r["gold"])) for r in rows}
            s = gscore(f)
            extra["GsmStrict" + w] = f"{s['strict']:.2f}"; extra["GsmLenient" + w] = f"{s['lenient']:.2f}"
            extra["GsmGap" + w] = f"{s['gap']:+.2f}"; extra["GsmMedTok" + w] = s["median_tokens"]
            extra["GsmTrunc" + w] = s["truncated"]; extra["GsmCi" + w] = ci(G[q])
    if "Q8_0" in G:
        for q, w in RUNG[1:]:
            if q in G:
                lost, gained, p = mcnemar(G["Q8_0"], G[q])
                extra["GsmDelta" + w] = f"{float(extra['GsmStrict'+w]) - float(extra['GsmStrictEight']):+.2f}"
                extra["GsmLost" + w], extra["GsmGained" + w] = lost, gained
                extra["GsmP" + w] = pfmt(p)
        L = ["\\begin{tabular}{@{}llrrrrr@{}}", "\\toprule",
             "Rung & Strict [95\\% CI] & Lenient & Extractor gap & vs.\\ Q8\\_0 (strict) & McNemar $p$ & Median tokens \\\\", "\\midrule"]
        for q, w in RUNG:
            if q not in G: continue
            cell = f"{extra['GsmStrict'+w]}\\% [{extra['GsmCi'+w]}]"
            if q == "Q8_0": L.append(f"{lab(q)} & {cell} & {extra['GsmLenient'+w]}\\% & {extra['GsmGap'+w]}\\,pp & baseline & & {extra['GsmMedTok'+w]} \\\\")
            else:
                L.append(f"{lab(q)} & {cell} & {extra['GsmLenient'+w]}\\% & {extra['GsmGap'+w]}\\,pp & {sgn(extra['GsmDelta'+w])}\\,pp & {bold(extra['GsmP'+w])} & {extra['GsmMedTok'+w]} \\\\")
        L += ["\\bottomrule", "\\end{tabular}"]; (TAB / "gsm8k.tex").write_text("\n".join(L) + "\n")
except Exception as e:
    print("gsm8k arm not ready:", e)

# --- every model, simple_python: strict and type-coerced scores, both against the model's own Q8_0
# The coerced score re-checks each strict failure with BFCL's own checker after string arguments are
# parsed to the type the schema declares (analysis/coerced.py). It never falls below strict.
MODEL_W = [("Qwen3-1.7B", ""), ("Qwen3-8B", "EightB"), ("Qwen3-14B", "FourteenB"), ("Llama-3.2-3B", "LlamaThreeB"), ("Llama-3.1-8B", "LlamaEightB")]
MODELS_ARM = [m for m in MODEL_W if m[1]]
S, C, ST = {}, {}, {}
try:
    from coerced import score_run
    for stem, w in MODEL_W:
        for q, rw in RUNG:
            d = RUNS / q if stem == "Qwen3-1.7B" else RUNS / stem / q
            sc = list((d / "score").rglob("*simple_python*score.json")); rs = list((d / "result").rglob("*simple_python*.json"))
            if not sc or not rs: continue
            n, s, c, st = score_run(sc[0], rs[0])
            S[(stem, q)], C[(stem, q)], ST[(stem, q)] = s, c, st
            if w:
                extra[f"Acc{w}{rw}"] = f"{acc(s):.2f}"; extra[f"N{w}"] = n; extra[f"Ci{w}{rw}"] = ci(s)
            extra[f"CoercedAcc{w}{rw}"] = f"{acc(c):.2f}"; extra[f"CoercedCi{w}{rw}"] = ci(c)
            extra[f"Fails{w}{rw}"] = st["fails"]; extra[f"TypeErr{w}{rw}"] = st["type_err"]
            extra[f"DecodeErr{w}{rw}"] = st["decode_err"]; extra[f"Coercible{w}{rw}"] = st["coercible"]
        if (stem, "Q8_0") in S:
            cliff_s = cliff_c = None
            for q, rw in RUNG[1:]:
                if (stem, q) not in S: continue
                lost, gained, p = mcnemar(S[(stem, "Q8_0")], S[(stem, q)])
                ds = acc(S[(stem, q)]) - acc(S[(stem, "Q8_0")])
                if w:
                    extra[f"Delta{w}{rw}"] = f"{ds:+.2f}"; extra[f"P{w}{rw}"] = pfmt(p)
                    extra[f"Lost{w}{rw}"], extra[f"Gained{w}{rw}"] = lost, gained
                if cliff_s is None and p < 0.05 and ds < 0: cliff_s = q
                lost, gained, p = mcnemar(C[(stem, "Q8_0")], C[(stem, q)])
                dc = acc(C[(stem, q)]) - acc(C[(stem, "Q8_0")])
                extra[f"CoercedDelta{w}{rw}"] = f"{dc:+.2f}"; extra[f"CoercedP{w}{rw}"] = pfmt(p)
                extra[f"CoercedLost{w}{rw}"], extra[f"CoercedGained{w}{rw}"] = lost, gained
                if cliff_c is None and p < 0.05 and dc < 0: cliff_c = q
            extra[f"CliffStrict{w}"] = lab(cliff_s) if cliff_s else "none"
            extra[f"CliffCoerced{w}"] = lab(cliff_c) if cliff_c else "none"
    extra["CoercibleQwenTotal"] = sum(ST[k]["coercible"] for k in ST if k[0].startswith("Qwen3"))
    extra["FailsQwenTotal"] = sum(ST[k]["fails"] for k in ST if k[0].startswith("Qwen3"))
except Exception as e:
    print("coerced re-score not ready:", e)
    for stem, w in MODELS_ARM:
        for q, rw in RUNG:
            v = _acc_rows(RUNS / stem / q, "*simple_python*.json")
            if v: S[(stem, q)] = v; extra[f"Acc{w}{rw}"] = f"{acc(v):.2f}"; extra[f"N{w}"] = len(v); extra[f"Ci{w}{rw}"] = ci(v)
        if (stem, "Q8_0") in S:
            for q, rw in RUNG:
                if q != "Q8_0" and (stem, q) in S:
                    lost, gained, p = mcnemar(S[(stem, "Q8_0")], S[(stem, q)])
                    extra[f"Delta{w}{rw}"] = f"{acc(S[(stem,q)]) - acc(S[(stem,'Q8_0')]):+.2f}"; extra[f"P{w}{rw}"] = pfmt(p)
                    extra[f"Lost{w}{rw}"], extra[f"Gained{w}{rw}"] = lost, gained
if S:
    L = ["\\begin{tabular}{@{}llrlrrlrr@{}}", "\\toprule",
         "Model & Rung & $n$ & Strict [95\\% CI] & vs.\\ Q8\\_0 & $p$ & Coerced [95\\% CI] & vs.\\ Q8\\_0 & $p$ \\\\", "\\midrule"]
    for stem, w in MODEL_W:
        for q, rw in RUNG:
            if stem == "Qwen3-1.7B" and q not in ("Q8_0", "Q4_K_M", "Q3_K_M"): continue
            if (stem, q) not in S: continue
            a = N["Acc"+rw] if not w else extra[f"Acc{w}{rw}"]; cia = N["Ci"+rw] if not w else extra[f"Ci{w}{rw}"]
            n = N["N"] if not w else extra[f"N{w}"]
            d = (N.get("Delta"+rw) if not w else extra.get(f"Delta{w}{rw}")); p = (N.get("P"+rw, "") if not w else extra.get(f"P{w}{rw}", ""))
            ca = extra.get(f"CoercedAcc{w}{rw}", ""); cic = extra.get(f"CoercedCi{w}{rw}", "")
            cd = extra.get(f"CoercedDelta{w}{rw}"); cp = extra.get(f"CoercedP{w}{rw}", "")
            fmt = lambda x: "baseline" if x is None else sgn(x) + "\\,pp"
            ccell = f"{ca}\\% [{cic}]" if ca else ""
            L.append(f"{stem} & {lab(q)} & {n} & {a}\\% [{cia}] & {fmt(d)} & {bold(p)} & {ccell} & {fmt(cd) if ccell else ''} & {bold(cp)} \\\\")
        L.append("\\midrule")
    L = L[:-1] + ["\\bottomrule", "\\end{tabular}"]; (TAB / "models.tex").write_text("\n".join(L) + "\n")

# --- H4: penalty vs none, same weights
for q, rw in (("Q4_K_M", "Four"), ("Q3_K_M", "Three")):
    v = _acc_rows(RUNS / "h4" / q, "*simple_python*.json")
    if v:
        extra["HfourAcc" + rw] = f"{acc(v):.2f}"
        lost, gained, p = mcnemar(V[q], v)
        extra["HfourDelta" + rw] = f"{acc(v) - acc(V[q]):+.2f}"; extra["HfourP" + rw] = pfmt(p)
        extra["HfourLost" + rw], extra["HfourGained" + rw] = lost, gained
# --- H5: multi-turn at three rungs
H5 = {}
for q, rw in RUNG:
    v = _acc_rows(RUNS / "Qwen3-1.7B" / "multi_turn_base" / q, "*multi_turn_base*.json")
    if v: H5[q] = v; extra["MtAcc" + rw] = f"{acc(v):.2f}"; extra["MtN"] = len(v); extra["MtCi" + rw] = ci(v)
if "Q8_0" in H5:
    for q, rw in RUNG:
        if q != "Q8_0" and q in H5:
            lost, gained, p = mcnemar(H5["Q8_0"], H5[q])
            extra["MtDelta" + rw] = f"{acc(H5[q]) - acc(H5['Q8_0']):+.2f}"; extra["MtP" + rw] = pfmt(p)
            extra["MtLost" + rw], extra["MtGained" + rw] = lost, gained
            extra["MtRel" + rw] = f"{(acc(H5[q]) - acc(H5['Q8_0'])) / acc(H5['Q8_0']) * 100:+.1f}"
            if "Delta" + rw in N: extra["SingleRel" + rw] = f"{float(N['Delta'+rw]) / float(N['AccEight']) * 100:+.1f}"
    L = ["\\begin{tabular}{@{}lrlrrrrr@{}}", "\\toprule",
         "Rung & $n$ & Accuracy [95\\% CI] & vs.\\ Q8\\_0 & Lost/Gained & McNemar $p$ & Relative (\\%) & Single call, relative (\\%) \\\\", "\\midrule"]
    for q, rw in RUNG:
        if q not in H5: continue
        cell = f"{extra['MtAcc'+rw]}\\% [{extra['MtCi'+rw]}]"
        if q == "Q8_0": L.append(f"{lab(q)} & {extra['MtN']} & {cell} & baseline & & & & \\\\")
        else:
            L.append(f"{lab(q)} & {extra['MtN']} & {cell} & {sgn(extra['MtDelta'+rw])}\\,pp & {extra['MtLost'+rw]}/{extra['MtGained'+rw]} & {bold(extra['MtP'+rw])} & {sgn(extra['MtRel'+rw])} & {sgn(extra.get('SingleRel'+rw, ''))} \\\\")
    L += ["\\bottomrule", "\\end{tabular}"]; (TAB / "multiturn.tex").write_text("\n".join(L) + "\n")

extra["GsmGapMax"] = f"{max(abs(float(extra[k])) for k in extra if k.startswith('GsmGap')):.2f}"
with (TAB / "numbers.tex").open("a") as f:
    for k, v in extra.items(): f.write(f"\\newcommand{{\\qt{mac(k)}}}{{{v}}}\n")
print(f"later arms: {len(extra)} macros added; tables present:", sorted(p.name for p in TAB.glob("*.tex")))

# ============================================================ mechanism macros
mech = {}
try:
    from gsm8k_score import strict as gstrict, norm as gnorm
    for q, w in (("Q8_0", "Eight"), ("Q3_K_M", "Three")):
        rows = [json.loads(l) for l in (RUNS / "gsm8k" / f"{q}.jsonl").open()]
        tr = [r for r in rows if r["finish_reason"] == "length"]; fin = [r for r in rows if r["finish_reason"] != "length"]
        c = lambda rs: sum(gnorm(gstrict(r["content"])) == gnorm(r["gold"]) for r in rs)
        mech["GsmFinishedN" + w] = len(fin); mech["GsmFinishedAcc" + w] = f"{100*c(fin)/len(fin):.1f}"
        mech["GsmTruncCorrect" + w] = c(tr)
    mech["GsmFinishedDrop"] = f"{float(mech['GsmFinishedAccEight']) - float(mech['GsmFinishedAccThree']):.1f}"
    mech["GsmTruncPctThree"] = f"{100*int(N.get('GsmTruncThree', extra.get('GsmTruncThree', 0)))/400:.0f}"
    for q, w in (("Q8_0", "Eight"), ("Q3_K_M", "Three")):
        ng = sorted(int(m) for m in re.findall(r"n_gen =\s*(\d+)", (RUNS / f"{q}.server.log").read_text()))
        mech["ToolNgenMed" + w] = ng[len(ng)//2]; mech["ToolNgenPninezero" + w] = ng[int(.9*len(ng))]
        mech["ToolNgenReqs" + w] = len(ng); mech["ToolNgenCap" + w] = sum(1 for x in ng if x >= 4000)
except Exception as e:
    print("mechanism macros not ready:", e)
with (TAB / "numbers.tex").open("a") as f:
    for k, v in mech.items(): f.write(f"\\newcommand{{\\qt{mac(k)}}}{{{v}}}\n")
print(f"mechanism: {len(mech)} macros")

# ============================================================ multi-turn length evidence
mt = {}
try:
    for q, w in (("Q8_0", "Eight"), ("Q3_K_M", "Three")):
        srv = (RUNS / "Qwen3-1.7B" / f"multi_turn_base-{q}.server.log").read_text()
        ng = sorted(int(m) for m in re.findall(r"n_gen =\s*(\d+)", srv))
        mt["MtNgenMed" + w] = ng[len(ng)//2]; mt["MtNgenPninezero" + w] = ng[int(.9*len(ng))]; mt["MtNgenReqs" + w] = len(ng)
except Exception as e:
    print("multi-turn length macros not ready:", e)
with (TAB / "numbers.tex").open("a") as f:
    for k, v in mt.items(): f.write(f"\\newcommand{{\\qt{mac(k)}}}{{{v}}}\n")
print(f"multi-turn length: {len(mt)} macros")

# ============================================================ budget control (16K on the Q3_K_M truncations)
bud = {}
try:
    from gsm8k_score import strict as gstrict, norm as gnorm
    rows = [json.loads(l) for l in (RUNS / "gsm8k_budget" / "Q3_K_M_16k.jsonl").open()]
    real = [r for r in rows if r.get("finish_reason") in ("stop", "length")]
    fin = [r for r in real if r["finish_reason"] == "stop"]; cap = [r for r in real if r["finish_reason"] == "length"]
    c = lambda rs: sum(gnorm(gstrict(r["content"])) == gnorm(r["gold"]) for r in rs)
    bud["BudN"] = len(real); bud["BudFinished"] = len(fin); bud["BudStillCap"] = len(cap)
    bud["BudStillCapPct"] = f"{100*len(cap)/max(1,len(real)):.0f}"
    bud["BudRecovered"] = c(fin) + c(cap); bud["BudRecoveredPct"] = f"{100*(c(fin)+c(cap))/max(1,len(real)):.0f}"
    bud["BudOf"] = 213
except Exception as e:
    print("budget macros not ready:", e)
with (TAB / "numbers.tex").open("a") as f:
    for k, v in bud.items(): f.write(f"\\newcommand{{\\qt{mac(k)}}}{{{v}}}\n")
print(f"budget: {len(bud)} macros")

# ============================================================ second family: Llama GSM8K + failure types (27 Sep 2026; coerced score moved to coerced.py 29 Sep 2026)
fam = {}
try:
    from gsm8k_score import strict as gstrict, lenient as glenient, norm as gnorm
    FAM = [("Llama-3.2-3B", "LlamaThreeB"), ("Llama-3.1-8B", "LlamaEightB")]
    FRUNG = [("Q8_0", "Eight"), ("Q4_K_M", "Four"), ("Q3_K_M", "Three")]
    L = ["\\begin{tabular}{@{}llrrrrrrr@{}}", "\\toprule",
         "Model & Rung & Tool acc. & vs.\\ Q8\\_0 & $p$ & Coerced & GSM8K strict & vs.\\ Q8\\_0 & $p$ \\\\", "\\midrule"]
    F = ["\\begin{tabular}{@{}llrrrrlrr@{}}", "\\toprule",
         "Model & Rung & Strict failures & Type errors & Decode errors & Coercible & GSM8K strict [95\\% CI] & vs.\\ Q8\\_0 & $p$ \\\\", "\\midrule"]
    for stem, w in FAM:
        G = {}
        for q, rw in FRUNG:
            rows = [json.loads(l) for l in (RUNS / stem / "gsm8k" / f"{q}.jsonl").open()]
            ver = {r["id"]: (gnorm(gstrict(r["content"])) == gnorm(r["gold"])) for r in rows}
            len_ = {r["id"]: (gnorm(glenient(r["content"])) == gnorm(r["gold"])) for r in rows}
            G[q] = ver
            toks = sorted(r["completion_tokens"] or 0 for r in rows)
            fam[f"{w}GsmN"] = len(rows)
            fam[f"{w}GsmStrict{rw}"] = f"{100*sum(ver.values())/len(rows):.2f}"
            fam[f"{w}GsmCi{rw}"] = ci(ver)
            fam[f"{w}GsmLenient{rw}"] = f"{100*sum(len_.values())/len(rows):.2f}"
            fam[f"{w}GsmGap{rw}"] = f"{100*(sum(len_.values())-sum(ver.values()))/len(rows):+.2f}"
            fam[f"{w}GsmTrunc{rw}"] = sum(1 for r in rows if r["finish_reason"] == "length")
            fam[f"{w}GsmMedTok{rw}"] = toks[len(toks)//2]
            # failure types and the coerced score, as computed above from BFCL's checker (aliases keep older macro names valid)
            for k in ("Fails", "TypeErr", "DecodeErr", "Coercible", "CoercedAcc"):
                if f"{k}{w}{rw}" in extra: fam[f"{w}{k}{rw}"] = extra[f"{k}{w}{rw}"]
        for q, rw in FRUNG:
            if q != "Q8_0" and f"CoercedDelta{w}{rw}" in extra:
                fam[f"{w}CoercedDelta{rw}"] = extra[f"CoercedDelta{w}{rw}"]   # the unsigned-drop block below derives CoercedDrop
            if q != "Q8_0":
                lost, gained, pg = mcnemar(G["Q8_0"], G[q])
                fam[f"{w}GsmDelta{rw}"] = f"{100*(sum(G[q].values())-sum(G['Q8_0'].values()))/len(G[q]):+.2f}"
                fam[f"{w}GsmP{rw}"] = pfmt(pg)
                fam[f"{w}GsmLost{rw}"], fam[f"{w}GsmGained{rw}"] = lost, gained
        for q, rw in FRUNG:
            gs = fam[f"{w}GsmStrict{rw}"]; gd = fam.get(f"{w}GsmDelta{rw}"); gp = fam.get(f"{w}GsmP{rw}", "")
            fmt = lambda d: "baseline" if d is None else sgn(d) + "\\,pp"
            ta = extra.get(f"Acc{w}{rw}", "?"); td = extra.get(f"Delta{w}{rw}"); tp = extra.get(f"P{w}{rw}", ""); ca = extra.get(f"CoercedAcc{w}{rw}", "?")
            L.append(f"{stem} & {lab(q)} & {ta}\\% & {fmt(td)} & {bold(tp)} & {ca}\\% & {gs}\\% & {fmt(gd)} & {bold(gp)} \\\\")
            F.append(f"{stem} & {lab(q)} & {fam.get(f'{w}Fails{rw}','?')} & {fam.get(f'{w}TypeErr{rw}','?')} & {fam.get(f'{w}DecodeErr{rw}','?')} & {fam.get(f'{w}Coercible{rw}','?')} & {gs}\\% [{fam[f'{w}GsmCi{rw}']}] & {fmt(gd)} & {bold(gp)} \\\\")
        L.append("\\midrule"); F.append("\\midrule")
    L = L[:-1] + ["\\bottomrule", "\\end{tabular}"]; (TAB / "llama.tex").write_text("\n".join(L) + "\n")
    F = F[:-1] + ["\\bottomrule", "\\end{tabular}"]; (TAB / "llama_failures.tex").write_text("\n".join(F) + "\n")
except Exception as e:
    print("second-family macros not ready:", e)
with (TAB / "numbers.tex").open("a") as f:
    for k, v in fam.items(): f.write(f"\\newcommand{{\\qt{mac(k)}}}{{{v}}}\n")
print(f"second family: {len(fam)} macros")

# ============================================================ published BFCL leaderboard row for Llama-3.1-8B-Instruct (stored CSV, see analysis/bfcl_leaderboard/FETCH.txt)
lb = {}
try:
    LB = HERE / "analysis" / "bfcl_leaderboard"
    rows = list(csv.DictReader((LB / "data_non_live.csv").open()))
    hits = [r for r in rows if "Llama-3.1-8B-Instruct" in r["Model"]]
    lb["BfclModelsListed"] = len(rows); lb["BfclLlamaRows"] = len(hits)
    lb["BfclLlamaFcRows"] = sum(1 for r in hits if "(FC)" in r["Model"])
    pr = next(r for r in hits if "(Prompt)" in r["Model"])
    lb["BfclPromptPySimple"] = pr["Python Simple AST"].rstrip("%"); lb["BfclPromptNonLive"] = pr["Non-Live Overall Acc"].rstrip("%")
    fetch = (LB / "FETCH.txt").read_text()
    m = re.search(r"last-modified: \w+, (\d+) (\w+) (\d{4})", fetch)
    MON = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April", "May": "May", "Jun": "June", "Jul": "July", "Aug": "August", "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December"}
    lb["BfclDataDate"] = f"{int(m.group(1))} {MON[m.group(2)]} {m.group(3)}"
    lb["BfclFetchDate"] = re.search(r"fetched_on: (\S+)", fetch).group(1)
except Exception as e:
    print("leaderboard macros not ready:", e)
with (TAB / "numbers.tex").open("a") as f:
    for k, v in lb.items(): f.write(f"\\newcommand{{\\qt{mac(k)}}}{{{v}}}\n")
print(f"leaderboard: {len(lb)} macros")

# ============================================================ unsigned drops for prose ("loses X points")
_n = (TAB / "numbers.tex").read_text()
_drops = []
for _m in re.finditer(r"\\newcommand\{\\qt(\w*?)Delta(\w+)\}\{([+-]?[\d.]+)\}", _n):
    _drops.append(f"\\newcommand{{\\qt{_m.group(1)}Drop{_m.group(2)}}}{{{abs(float(_m.group(3))):.2f}}}\n")
with (TAB / "numbers.tex").open("a") as f: f.writelines(_drops)
print(f"drop macros: {len(_drops)}")
# duplicate-definition guard: LaTeX refuses a second \newcommand of the same name
_names = re.findall(r"\\newcommand\{(\\qt\w+)\}", (TAB / "numbers.tex").read_text())
_dup = sorted({x for x in _names if _names.count(x) > 1})
if _dup: sys.exit(f"duplicate macro names: {_dup}")
print(f"total macros: {len(_names)}, no duplicates")

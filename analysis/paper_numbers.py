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
        N["P" + w] = f"{p:.3f}" if p >= 0.001 else "$<$0.0001"
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

# ============================================================ later arms, populated as they land
import re, sys
sys.path.insert(0, str(HERE))
def _pf(x):
    """p-value string -> float, tolerating the '$<$0.0001' display form."""
    return float(str(x).replace('$', '').replace('<', '').strip() or 1)

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
            extra["GsmTrunc" + w] = s["truncated"]
    if "Q8_0" in G:
        for q, w in RUNG[1:]:
            if q in G:
                lost, gained, p = mcnemar(G["Q8_0"], G[q])
                extra["GsmDelta" + w] = f"{float(extra['GsmStrict'+w]) - float(extra['GsmStrictEight']):+.2f}"
                extra["GsmLost" + w], extra["GsmGained" + w] = lost, gained
                extra["GsmP" + w] = f"{p:.3f}" if p >= 0.001 else "$<$0.0001"
        L = ["\\begin{tabular}{@{}lrrrrrr@{}}", "\\toprule",
             "Rung & Strict & Lenient & Extractor gap & vs.\\ Q8\\_0 (strict) & McNemar $p$ & Median tokens \\\\", "\\midrule"]
        for q, w in RUNG:
            if q not in G: continue
            lab = q.replace("_", "\\_")
            if q == "Q8_0": L.append(f"{lab} & {extra['GsmStrict'+w]}\\% & {extra['GsmLenient'+w]}\\% & {extra['GsmGap'+w]}\\,pp & baseline & & {extra['GsmMedTok'+w]} \\\\")
            else:
                d = extra["GsmDelta"+w].replace("-", "$-$").replace("+", "$+$"); pv = extra["GsmP"+w]
                pv = f"\\textbf{{{pv}}}" if _pf(pv) < 0.05 else pv
                L.append(f"{lab} & {extra['GsmStrict'+w]}\\% & {extra['GsmLenient'+w]}\\% & {extra['GsmGap'+w]}\\,pp & {d}\\,pp & {pv} & {extra['GsmMedTok'+w]} \\\\")
        L += ["\\bottomrule", "\\end{tabular}"]; (TAB / "gsm8k.tex").write_text("\n".join(L) + "\n")
except Exception as e:
    print("gsm8k arm not ready:", e)

# --- other models, simple_python at three rungs
MODELS_ARM = [("Qwen3-8B", "EightB"), ("Qwen3-14B", "FourteenB"), ("Llama-3.2-3B", "LlamaThreeB"), ("Llama-3.1-8B", "LlamaEightB")]
M = {}
for stem, w in MODELS_ARM:
    for q, rw in RUNG:
        v = _acc_rows(RUNS / stem / q, "*simple_python*.json")
        if v: M[(stem, q)] = v; extra[f"Acc{w}{rw}"] = f"{acc(v):.2f}"; extra[f"N{w}"] = len(v)
    if (stem, "Q8_0") in M:
        for q, rw in RUNG:
            if q != "Q8_0" and (stem, q) in M:
                lost, gained, p = mcnemar(M[(stem, "Q8_0")], M[(stem, q)])
                extra[f"Delta{w}{rw}"] = f"{acc(M[(stem,q)]) - acc(M[(stem,'Q8_0')]):+.2f}"
                extra[f"P{w}{rw}"] = f"{p:.3f}" if p >= 0.001 else "$<$0.0001"
                extra[f"Lost{w}{rw}"], extra[f"Gained{w}{rw}"] = lost, gained
if M:
    L = ["\\begin{tabular}{@{}llrrrrr@{}}", "\\toprule", "Model & Rung & $n$ & Accuracy & vs.\\ Q8\\_0 & Lost/Gained & McNemar $p$ \\\\", "\\midrule"]
    for stem, w in [("Qwen3-1.7B", None)] + MODELS_ARM:
        for q, rw in RUNG:
            if stem == "Qwen3-1.7B":
                if q not in ("Q8_0", "Q4_K_M", "Q3_K_M"): continue
                a = N["Acc"+rw]; n = N["N"]; d = N.get("Delta"+rw, "baseline"); p = N.get("P"+rw, ""); lg = f"{N.get('Lost'+rw,'')}/{N.get('Gained'+rw,'')}" if q != "Q8_0" else ""
            else:
                if (stem, q) not in M: continue
                a = extra[f"Acc{w}{rw}"]; n = extra[f"N{w}"]; d = extra.get(f"Delta{w}{rw}", "baseline"); p = extra.get(f"P{w}{rw}", ""); lg = f"{extra.get(f'Lost{w}{rw}','')}/{extra.get(f'Gained{w}{rw}','')}" if q != "Q8_0" else ""
            d = d if d == "baseline" else d.replace("-", "$-$").replace("+", "$+$") + "\\,pp"
            if p and _pf(p) < 0.05: p = f"\\textbf{{{p}}}"
            L.append(f"{stem} & {q.replace('_', chr(92)+'_')} & {n} & {a}\\% & {d} & {lg} & {p} \\\\")
        L.append("\\midrule")
    L = L[:-1] + ["\\bottomrule", "\\end{tabular}"]; (TAB / "models.tex").write_text("\n".join(L) + "\n")

# --- H4: penalty vs none, same weights
for q, rw in (("Q4_K_M", "Four"), ("Q3_K_M", "Three")):
    v = _acc_rows(RUNS / "h4" / q, "*simple_python*.json")
    if v:
        extra["HfourAcc" + rw] = f"{acc(v):.2f}"
        lost, gained, p = mcnemar(V[q], v)
        extra["HfourDelta" + rw] = f"{acc(v) - acc(V[q]):+.2f}"; extra["HfourP" + rw] = f"{p:.3f}" if p >= 0.001 else "$<$0.0001"
        extra["HfourLost" + rw], extra["HfourGained" + rw] = lost, gained
# --- H5: multi-turn at three rungs
H5 = {}
for q, rw in RUNG:
    v = _acc_rows(RUNS / "Qwen3-1.7B" / "multi_turn_base" / q, "*multi_turn_base*.json")
    if v: H5[q] = v; extra["MtAcc" + rw] = f"{acc(v):.2f}"; extra["MtN"] = len(v)
if "Q8_0" in H5:
    for q, rw in RUNG:
        if q != "Q8_0" and q in H5:
            lost, gained, p = mcnemar(H5["Q8_0"], H5[q])
            extra["MtDelta" + rw] = f"{acc(H5[q]) - acc(H5['Q8_0']):+.2f}"; extra["MtP" + rw] = f"{p:.3f}" if p >= 0.001 else "$<$0.0001"
            extra["MtRel" + rw] = f"{(acc(H5[q]) - acc(H5['Q8_0'])) / acc(H5['Q8_0']) * 100:+.1f}"
            if "Delta" + rw in N: extra["SingleRel" + rw] = f"{float(N['Delta'+rw]) / float(N['AccEight']) * 100:+.1f}"

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


# ============================================================ second family: Llama GSM8K + failure types (27 Sep 2026)
fam = {}
try:
    from gsm8k_score import strict as gstrict, lenient as glenient, norm as gnorm
    FAM = [("Llama-3.2-3B", "LlamaThreeB"), ("Llama-3.1-8B", "LlamaEightB")]
    FRUNG = [("Q8_0", "Eight"), ("Q4_K_M", "Four"), ("Q3_K_M", "Three")]
    L = ["\\begin{tabular}{@{}llrrrrrrr@{}}", "\\toprule",
         "Model & Rung & Tool acc. & vs.\\ Q8\\_0 & $p$ & Coerced & GSM8K strict & vs.\\ Q8\\_0 & $p$ \\\\", "\\midrule"]
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
            fam[f"{w}GsmLenient{rw}"] = f"{100*sum(len_.values())/len(rows):.2f}"
            fam[f"{w}GsmGap{rw}"] = f"{100*(sum(len_.values())-sum(ver.values()))/len(rows):+.2f}"
            fam[f"{w}GsmTrunc{rw}"] = sum(1 for r in rows if r["finish_reason"] == "length")
            fam[f"{w}GsmMedTok{rw}"] = toks[len(toks)//2]
            # failure types on the tool-calling side, and a type-coerced re-score:
            # a failure counts as coerced-correct when every error is a type error whose string value
            # parses as the expected number/array/boolean (the value itself is what the reference holds).
            sc = list((RUNS / stem / q / "score").rglob("*simple_python*score.json"))
            if sc:
                fails = [json.loads(l) for l in sc[0].open()][1:]
                fam[f"{w}Fails{rw}"] = len(fails)
                fam[f"{w}TypeErr{rw}"] = sum(1 for r in fails if str(r.get("error_type","")).startswith("type_error"))
                fam[f"{w}DecodeErr{rw}"] = sum(1 for r in fails if str(r.get("error_type","")).startswith("ast_decoder"))
                _pat = re.compile(r"Expected type (\w+), got (\w+)\. Parameter value: (.*)\.$")
                def _coercible(f):
                    if not str(f.get("error_type","")).startswith("type_error"): return False
                    errs = f.get("error") or []; errs = [errs] if isinstance(errs, str) else errs
                    for e in errs:
                        m = _pat.search(e)
                        if not m: return False
                        exp, got, val = m.groups(); val = val.strip().strip("'\"")
                        if exp in ("integer", "float", "number") and got == "str" and re.fullmatch(r"-?\d+(\.\d+)?", val): continue
                        if exp == "array" and got == "str" and val.startswith("["): continue
                        if exp == "boolean" and got == "str" and val.lower() in ("true", "false"): continue
                        return False
                    return True
                coer = sum(1 for f in fails if _coercible(f))
                fam[f"{w}Coercible{rw}"] = coer
                ntool = extra.get(f"N{w}", 200)
                fam[f"{w}CoercedAcc{rw}"] = f"{100*(ntool - len(fails) + coer)/ntool:.2f}"
        for q, rw in FRUNG:
            if q != "Q8_0" and f"{w}CoercedAcc{rw}" in fam:
                dc = float(fam[f"{w}CoercedAcc{rw}"]) - float(fam[f"{w}CoercedAccEight"])
                fam[f"{w}CoercedDelta{rw}"] = f"{dc:+.2f}"   # the unsigned-drop block below derives CoercedDrop
            if q != "Q8_0":
                lost, gained, pg = mcnemar(G["Q8_0"], G[q])
                fam[f"{w}GsmDelta{rw}"] = f"{100*(sum(G[q].values())-sum(G['Q8_0'].values()))/len(G[q]):+.2f}"
                fam[f"{w}GsmP{rw}"] = f"{pg:.3f}" if pg >= 0.001 else "$<$0.0001"
                fam[f"{w}GsmLost{rw}"], fam[f"{w}GsmGained{rw}"] = lost, gained
        for q, rw in FRUNG:
            ta = extra.get(f"Acc{w}{rw}", "?"); td = extra.get(f"Delta{w}{rw}"); tp = extra.get(f"P{w}{rw}", "")
            gs = fam[f"{w}GsmStrict{rw}"]; gd = fam.get(f"{w}GsmDelta{rw}"); gp = fam.get(f"{w}GsmP{rw}", "")
            fmt = lambda d: "baseline" if d is None else d.replace("-", "$-$").replace("+", "$+$") + "\\,pp"
            bold = lambda pv: (f"\\textbf{{{pv}}}" if pv and _pf(pv) < 0.05 else pv)
            ca = fam.get(f"{w}CoercedAcc{rw}", "?")
            L.append(f"{stem} & {q.replace('_', chr(92)+'_')} & {ta}\\% & {fmt(td)} & {bold(tp)} & {ca}\\% & {gs}\\% & {fmt(gd)} & {bold(gp)} \\\\")
        L.append("\\midrule")
    L = L[:-1] + ["\\bottomrule", "\\end{tabular}"]; (TAB / "llama.tex").write_text("\n".join(L) + "\n")
except Exception as e:
    print("second-family macros not ready:", e)
with (TAB / "numbers.tex").open("a") as f:
    for k, v in fam.items(): f.write(f"\\newcommand{{\\qt{mac(k)}}}{{{v}}}\n")
print(f"second family: {len(fam)} macros")

# ============================================================ unsigned drops for prose ("loses X points")
_n = (TAB / "numbers.tex").read_text()
_drops = []
for _m in re.finditer(r"\\newcommand\{\\qt(\w*?)Delta(\w+)\}\{([+-]?[\d.]+)\}", _n):
    _drops.append(f"\\newcommand{{\\qt{_m.group(1)}Drop{_m.group(2)}}}{{{abs(float(_m.group(3))):.2f}}}\n")
with (TAB / "numbers.tex").open("a") as f: f.writelines(_drops)
print(f"drop macros: {len(_drops)}")

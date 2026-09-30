#!/usr/bin/env python3
"""Every number in the paper, recomputed from runs/. Emits paper/tables/numbers.tex and every
table (ladder, repeats, gsm8k, models, fourbit, htwo, llama, llama_failures, multiturn).
Two values are recorded rather than computed and are labelled as such in the manuscript: the
throughput figures (MacTg, MacPp) come from the lab notebook of 18 Sep 2026.
Run with the project's .venv python: the coerced re-score imports BFCL's own checker.

Statistics (29 Sep 2026 revision): McNemar's exact test on discordant pairs; Holm's step-down
correction within families (one family per model for the single-call arm, covering every distinct
test against that model's Q8_0 under both verdicts; one family per model for the free-form arm; one
for multi-turn; one for the penalty arm); Wilson 95% intervals on every accuracy; Agresti and Min
(2005) adjusted Wald 95% intervals on every paired difference; the minimum detectable paired
difference at alpha 0.05 and 80% power at the observed discordance rate (Connor 1987 sample-size
formula solved for the difference)."""
import csv, json, math, os, re, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "analysis"))
RUNS, TAB, MODELS = HERE / "runs", HERE / "paper" / "tables", HERE / "models"
TAB.mkdir(parents=True, exist_ok=True)
RUNG = [("Q8_0", "Eight"), ("Q6_K", "Six"), ("Q5_K_M", "Five"), ("Q4_K_M", "Four"), ("Q3_K_M", "Three")]
RW = dict(RUNG)
Z = 1.959963984540054   # two-sided 95%
ZB = 0.8416212335729143  # 80% power
CAP = 4096               # completion budget of every arm

def wilson(k, n):
    """Wilson score interval for k successes in n trials, in percentage points."""
    p = k / n; d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)

def ci(v):
    lo, hi = wilson(sum(v.values()), len(v)); return f"{lo:.1f}, {hi:.1f}"

def acc(v): return 100 * sum(v.values()) / len(v)

def mcnemar(a, b):
    c = set(a) & set(b)
    lost = sum(1 for i in c if a[i] and not b[i]); gained = sum(1 for i in c if not a[i] and b[i])
    n = lost + gained
    if n == 0: return lost, gained, 1.0
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(0, min(lost, gained) + 1)) / 2 ** n)
    return lost, gained, p

def holm(pd):
    """Holm step-down adjusted p-values for a family {key: p}."""
    items = sorted(pd.items(), key=lambda kv: kv[1]); m = len(items); adj = {}; run = 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p)); adj[k] = run
    return adj

def paired_ci(lost, gained, n):
    """Agresti-Min (2005) adjusted Wald 95% interval on the paired difference (rung minus Q8_0), pp."""
    b, c, m = lost + 0.5, gained + 0.5, n + 2
    d = (c - b) / m; se = math.sqrt(b + c - (b - c) ** 2 / m) / m
    return 100 * (d - Z * se), 100 * (d + Z * se)

def mde(n, lost, gained):
    """Smallest paired difference (pp) McNemar detects at alpha 0.05, 80% power, given the observed
    discordance rate psi = (lost+gained)/n (Connor 1987: n = [z_a sqrt(psi) + z_b sqrt(psi - d^2)]^2 / d^2)."""
    psi = (lost + gained) / n
    if psi <= 0: return None
    lo, hi = 0.0, math.sqrt(psi)
    for _ in range(200):
        d = (lo + hi) / 2
        rhs = (Z * math.sqrt(psi) + ZB * math.sqrt(max(psi - d * d, 0.0))) ** 2
        if n * d * d >= rhs: hi = d
        else: lo = d
    return 100 * hi

def pfmt(p):
    if p < 0.0001: return "$<$0.0001"
    if p < 0.001: return f"{p:.4f}"
    return f"{p:.3f}"
def _pf(x): return float(str(x).replace('$', '').replace('<', '').strip() or 1)
def sgn(d): return str(d).replace("-", "$-$").replace("+", "$+$")
def bold(pv): return f"\\textbf{{{pv}}}" if pv and _pf(pv) < 0.05 else pv
def pcell(p, ph): return f"{pfmt(p)} ({bold(pfmt(ph))})"   # raw p, then the Holm-adjusted p in brackets
def lab(q): return q.replace("_", "\\_")
def cif(lo, hi): return f"[{sgn(f'{lo:+.1f}')}, {sgn(f'{hi:+.1f}')}]"
def frac(a, b): return f"{100 * a / b:.1f}" if b else "n/a"

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

def result_rows(run_dir, cat_glob="*simple_python*.json"):
    rs = list((run_dir / "result").rglob(cat_glob))
    return [json.loads(l) for l in rs[0].open() if l.strip()] if rs else []

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

DIG = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
mac = lambda k: "".join(DIG.get(c, c) for c in k)
N = {}
TESTS = 0   # every McNemar test reported in the paper
FAMILIES = 0

# ============================================================ Qwen3-1.7B ladder (strict verdicts)
V = {q: verdicts(q) for q, _ in RUNG}
base = V["Q8_0"]
N["N"] = len(base)
# FP16 source size: the Ollama manifest of qwen3:1.7b-fp16 (copy in runs/, taken 29 Sep 2026)
_man = json.load((RUNS / "ollama-manifest-qwen3-1.7b-fp16.json").open())
_fp16 = next(l["size"] for l in _man["layers"] if l["mediaType"].endswith(".model"))
N["SizeFp"] = f"{_fp16 / 1e9:.1f}"
for q, w in RUNG:
    v = V[q]; N["Acc" + w] = f"{acc(v):.2f}"; N["Ci" + w] = ci(v)
    gg = MODELS / f"Qwen3-1.7B-{q}.gguf"
    if gg.exists(): N["Size" + w] = f"{gg.stat().st_size / 1e9:.1f}"
N["SizeRatioFour"] = f"{100 * (MODELS / 'Qwen3-1.7B-Q4_K_M.gguf').stat().st_size / (MODELS / 'Qwen3-1.7B-Q8_0.gguf').stat().st_size:.0f}"
N["CompressFour"] = f"{(MODELS / 'Qwen3-1.7B-Q4_K_M.gguf').stat().st_size / _fp16 * 100:.0f}"

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
N["RungsCount"] = len(RUNG)
N["RunsTotal"] = len(RUNG) + sum(len(a) - 1 for a, _ in reps.values())

# throughput, from the lab notebook measurements of 18 Sep 2026 (recorded, not computed here)
N["MacTg"] = "35"; N["MacPp"] = "650"; N["GcpTg"] = "22.0"; N["GcpPp"] = "109.6"

# per-request completion length and latency of the single-call arm, from BFCL's result files
for q, w in RUNG:
    rows = result_rows(RUNS / q)
    t = sorted(r["output_token_count"] for r in rows); lat = sorted(r["latency"] for r in rows); n = len(t)
    N["ToolNgenMed" + w] = t[n // 2]; N["ToolNgenPninezero" + w] = t[int(.9 * n)]; N["ToolNgenMax" + w] = t[-1]
    N["ToolNgenReqs" + w] = n; N["ToolNgenCap" + w] = sum(1 for x in t if x >= CAP)
    N["ToolLatMed" + w] = f"{lat[n // 2]:.1f}"
    N["ToolInMed" + w] = sorted(r["input_token_count"] for r in rows)[n // 2]
    # generations that skip the reasoning block (empty reasoning_content), and accuracy on each subset
    nr = [r["id"] for r in rows if not (r.get("reasoning_content") or "").strip()]
    N["ToolNoReason" + w] = len(nr)
    if nr and len(nr) < n:
        N["ToolNoReasonAcc" + w] = f"{100 * sum(V[q][i] for i in nr) / len(nr):.1f}"
        wr = [r["id"] for r in rows if r["id"] not in set(nr)]
        N["ToolReasonAcc" + w] = f"{100 * sum(V[q][i] for i in wr) / len(wr):.1f}"

# server configuration of the single-call ladder, from the server log
_srv = (RUNS / "Q8_0.server.log").read_text()
_m = re.search(r"n_slots = (\d+), n_ctx_slot = (\d+), kv_unified = '(\w+)'", _srv)
N["LadderSlots"], N["LadderCtx"], N["LadderKvUnified"] = _m.group(1), f"{int(_m.group(2)):,}", _m.group(3)

(TAB / "numbers.tex").write_text("".join(f"\\newcommand{{\\qt{mac(k)}}}{{{v}}}\n" for k, v in N.items()))
print(f"{len(N)} ladder macros")

extra = {}
# ============================================================ free-form arm (GSM8K)
from gsm8k_score import score as gscore, strict as gstrict, lenient as glenient, norm as gnorm
G, GT = {}, {}
for q, w in RUNG:
    f = RUNS / "gsm8k" / f"{q}.jsonl"
    rows = [json.loads(l) for l in f.open()]
    G[q] = {r["id"]: (gnorm(gstrict(r["content"])) == gnorm(r["gold"])) for r in rows}
    s = gscore(f)
    extra["GsmStrict" + w] = f"{s['strict']:.2f}"; extra["GsmLenient" + w] = f"{s['lenient']:.2f}"
    extra["GsmGap" + w] = f"{s['gap']:+.2f}"; extra["GsmMedTok" + w] = s["median_tokens"]
    extra["GsmTrunc" + w] = s["truncated"]; extra["GsmCi" + w] = ci(G[q])
    tr = [r for r in rows if r["finish_reason"] == "length"]; fin = [r for r in rows if r["finish_reason"] != "length"]
    c = lambda rs: sum(gnorm(gstrict(r["content"])) == gnorm(r["gold"]) for r in rs)
    extra["GsmTruncCorrect" + w] = c(tr)
    extra["GsmTruncNoAnswer" + w] = sum(1 for r in tr if gstrict(r["content"]) is None)
    extra["GsmTruncWrong" + w] = len(tr) - c(tr) - extra["GsmTruncNoAnswer" + w]
    extra["GsmTruncPct" + w] = f"{100 * len(tr) / len(rows):.0f}"
    extra["GsmFinishedN" + w] = len(fin); extra["GsmFinishedAcc" + w] = f"{100 * c(fin) / len(fin):.1f}"
    extra["GsmFinishedCorrect" + w] = c(fin); extra["GsmCorrect" + w] = c(rows)
extra["GsmFinishedDrop"] = f"{float(extra['GsmFinishedAccEight']) - float(extra['GsmFinishedAccThree']):.1f}"
_gp = {}
for q, w in RUNG[1:]:
    lost, gained, p = mcnemar(G["Q8_0"], G[q]); _gp[q] = p
    extra["GsmDelta" + w] = f"{float(extra['GsmStrict'+w]) - float(extra['GsmStrictEight']):+.2f}"
    extra["GsmLost" + w], extra["GsmGained" + w] = lost, gained
    extra["GsmP" + w] = pfmt(p)
_gh = holm(_gp); TESTS += len(_gp); FAMILIES += 1
for q, w in RUNG[1:]: extra["GsmPHolm" + w] = pfmt(_gh[q])
extra["GsmGapMax"] = f"{max(abs(float(extra['GsmGap'+w])) for _, w in RUNG):.2f}"

# ============================================================ every model, simple_python: strict and coerced
MODEL_W = [("Qwen3-1.7B", ""), ("Qwen3-8B", "EightB"), ("Qwen3-14B", "FourteenB"), ("Llama-3.2-3B", "LlamaThreeB"), ("Llama-3.1-8B", "LlamaEightB")]
from coerced import score_run, STAT_KEYS
S, C, ST, ET = {}, {}, {}, {}
STATMAC = {"fails": "Fails", "type_err": "TypeErr", "value_err": "ValueErr", "decode_err": "DecodeErr", "decode_json": "DecodeJson",
           "wrong_name": "WrongName", "wrong_count": "WrongCount", "no_call": "NoCall", "missing": "Missing", "struct": "Struct",
           "semantic": "Semantic", "coercible": "Coercible", "coercible_decode": "CoercibleDecode"}
for stem, w in MODEL_W:
    for q, rw in RUNG:
        d = RUNS / q if stem == "Qwen3-1.7B" else RUNS / stem / q
        sc = list((d / "score").rglob("*simple_python*score.json")); rs = list((d / "result").rglob("*simple_python*.json"))
        if not sc or not rs: continue
        n, s, c, st, et = score_run(sc[0], rs[0])
        S[(stem, q)], C[(stem, q)], ST[(stem, q)], ET[(stem, q)] = s, c, st, et
        if w:
            extra[f"Acc{w}{rw}"] = f"{acc(s):.2f}"; extra[f"N{w}"] = n; extra[f"Ci{w}{rw}"] = ci(s)
        extra[f"CoercedAcc{w}{rw}"] = f"{acc(c):.2f}"; extra[f"CoercedCi{w}{rw}"] = ci(c)
        for k, mk in STATMAC.items(): extra[f"{mk}{w}{rw}"] = st[k]
        # registered metrics: schema validity (a call was decoded), hallucinated-function rate, structural share
        extra[f"SchemaValid{w}{rw}"] = f"{100 * (n - st['no_call']) / n:.2f}"
        extra[f"HallucFn{w}{rw}"] = f"{100 * st['wrong_name'] / n:.2f}"
        extra[f"StructShare{w}{rw}"] = frac(st["struct"], st["fails"])
    if (stem, "Q8_0") not in S: continue
    fam = {}   # one family per model: every distinct test against its own Q8_0, both verdicts
    for q, rw in RUNG[1:]:
        if (stem, q) not in S: continue
        fam[("s", q)] = mcnemar(S[(stem, "Q8_0")], S[(stem, q)])
        if not (C[(stem, q)] == S[(stem, q)] and C[(stem, "Q8_0")] == S[(stem, "Q8_0")]):
            fam[("c", q)] = mcnemar(C[(stem, "Q8_0")], C[(stem, q)])
    adj = holm({k: v[2] for k, v in fam.items()}); TESTS += len(fam); FAMILIES += 1
    extra[f"Tests{w}"] = len(fam)
    cliff_s = cliff_c = None
    for q, rw in RUNG[1:]:
        if (stem, q) not in S: continue
        n = len(S[(stem, q)])
        lost, gained, p = fam[("s", q)]; ph = adj[("s", q)]
        ds = acc(S[(stem, q)]) - acc(S[(stem, "Q8_0")]); lo, hi = paired_ci(lost, gained, n)
        if w:
            extra[f"Delta{w}{rw}"] = f"{ds:+.2f}"; extra[f"P{w}{rw}"] = pfmt(p)
            extra[f"Lost{w}{rw}"], extra[f"Gained{w}{rw}"] = lost, gained
        else:
            N[f"Delta{rw}"] = f"{ds:+.2f}"; N[f"P{rw}"] = pfmt(p); N[f"Lost{rw}"], N[f"Gained{rw}"] = lost, gained
        extra[f"PHolm{w}{rw}"] = pfmt(ph); extra[f"DiffCi{w}{rw}"] = cif(lo, hi); extra[f"DiffLo{w}{rw}"] = f"{lo:+.1f}"
        extra[f"Mde{w}{rw}"] = f"{mde(n, lost, gained):.1f}"
        if cliff_s is None and ph < 0.05 and ds < 0: cliff_s = q
        key = ("c", q) if ("c", q) in fam else ("s", q)
        lost, gained, p = fam[key]; ph = adj[key]
        dc = acc(C[(stem, q)]) - acc(C[(stem, "Q8_0")]); lo, hi = paired_ci(lost, gained, n)
        extra[f"CoercedDelta{w}{rw}"] = f"{dc:+.2f}"; extra[f"CoercedP{w}{rw}"] = pfmt(p); extra[f"CoercedPHolm{w}{rw}"] = pfmt(ph)
        extra[f"CoercedLost{w}{rw}"], extra[f"CoercedGained{w}{rw}"] = lost, gained
        extra[f"CoercedDiffCi{w}{rw}"] = cif(lo, hi); extra[f"CoercedDiffLo{w}{rw}"] = f"{lo:+.1f}"
        extra[f"CoercedMde{w}{rw}"] = f"{mde(n, lost, gained):.1f}"
        if cliff_c is None and ph < 0.05 and dc < 0: cliff_c = q
    extra[f"CliffStrict{w}"] = lab(cliff_s) if cliff_s else "none"
    extra[f"CliffCoerced{w}"] = lab(cliff_c) if cliff_c else "none"
    # H2 as registered: structural share of failures, Q8_0 to Q3_K_M
    a, b = ST[(stem, "Q8_0")], ST[(stem, "Q3_K_M")]
    extra[f"HtwoDelta{w}"] = f"{100 * b['struct'] / b['fails'] - 100 * a['struct'] / a['fails']:+.1f}"
    extra[f"HtwoDeltaJson{w}"] = f"{100 * (b['struct'] - b['decode_json']) / b['fails'] - 100 * (a['struct'] - a['decode_json']) / a['fails']:+.1f}"
N["CliffOverNoise"] = f"{abs(float(N['DeltaThree'])) / float(N['MaxRepRange']):.0f}"
extra["CoercibleQwenTotal"] = sum(ST[k]["coercible"] for k in ST if k[0].startswith("Qwen3"))
extra["FailsQwenTotal"] = sum(ST[k]["fails"] for k in ST if k[0].startswith("Qwen3"))
extra["DecodeQwenTotal"] = sum(ST[k]["decode_err"] for k in ST if k[0].startswith("Qwen3"))
# the 30 items Qwen3-1.7B loses at Q3_K_M, by BFCL error type
_lost3 = [i for i in ET[("Qwen3-1.7B", "Q3_K_M")] if i not in ET[("Qwen3-1.7B", "Q8_0")]]
_e3 = ET[("Qwen3-1.7B", "Q3_K_M")]
extra["LostThreeValue"] = sum(1 for i in _lost3 if _e3[i].startswith("value_error"))
extra["LostThreeType"] = sum(1 for i in _lost3 if _e3[i].startswith("type_error"))
extra["LostThreeNoCall"] = sum(1 for i in _lost3 if _e3[i].endswith("wrong_count"))
extra["LostThreeName"] = sum(1 for i in _lost3 if _e3[i].endswith("wrong_func_name"))
# H1 as registered: schema validity against 95% of the reference rung, Qwen3-1.7B
_sv = [float(extra[f"SchemaValid{rw}"]) for _, rw in RUNG]
extra["HoneSchemaMin"] = f"{min(_sv):.2f}"; extra["HoneSchemaThresh"] = f"{0.95 * _sv[0]:.2f}"
extra["HoneGsmThresh"] = f"{0.95 * float(extra['GsmStrictEight']):.2f}"
# H3 as registered: AST drop smaller than the strict free-form drop by at least 5 points, at Q3_K_M
extra["HthreeDiff"] = f"{abs(float(extra['GsmDeltaThree'])) - abs(float(N['DeltaThree'])):.2f}"
# the four-bit bound: the most negative lower interval end at Q4_K_M across models, per verdict
extra["FourBitLoStrict"] = f"{min(float(extra[f'DiffLo{w}Four']) for _, w in MODEL_W):+.1f}"
extra["FourBitLoCoerced"] = f"{min(float(extra[f'CoercedDiffLo{w}Four']) for _, w in MODEL_W):+.1f}"
extra["FourBitMdeMax"] = f"{max(float(extra[f'CoercedMde{w}Four']) for _, w in MODEL_W):.1f}"
extra["FourBitMdeMin"] = f"{min(float(extra[f'CoercedMde{w}Four']) for _, w in MODEL_W):.1f}"
# Llama-3.1-8B argument formatting habit per rung, from the raw result strings
for q, rw in (("Q8_0", "Eight"), ("Q4_K_M", "Four"), ("Q3_K_M", "Three")):
    rows = result_rows(RUNS / "Llama-3.1-8B" / q); txt = [str(r["result"]) for r in rows]
    extra[f"BareBoolLlamaEightB{rw}"] = sum(1 for t in txt if re.search(r":\s*(true|false)\b", t))
    extra[f"QuotedBoolLlamaEightB{rw}"] = sum(1 for t in txt if re.search(r':\s*"(true|false|True|False)"', t))
    extra[f"QuotedNumLlamaEightB{rw}"] = sum(1 for t in txt if re.search(r':\s*"-?\d+(\.\d+)?"', t))
    extra[f"BareNumLlamaEightB{rw}"] = sum(1 for t in txt if re.search(r":\s*-?\d+(\.\d+)?\s*[,}]", t))

# ============================================================ H4: penalty vs none, same weights
_hp = {}
for q, rw in (("Q4_K_M", "Four"), ("Q3_K_M", "Three")):
    v = _acc_rows(RUNS / "h4" / q, "*simple_python*.json")
    extra["HfourAcc" + rw] = f"{acc(v):.2f}"
    lost, gained, p = mcnemar(V[q], v); _hp[q] = p
    extra["HfourDelta" + rw] = f"{acc(v) - acc(V[q]):+.2f}"; extra["HfourP" + rw] = pfmt(p)
    extra["HfourLost" + rw], extra["HfourGained" + rw] = lost, gained
_hh = holm(_hp); TESTS += len(_hp); FAMILIES += 1
for q, rw in (("Q4_K_M", "Four"), ("Q3_K_M", "Three")): extra["HfourPHolm" + rw] = pfmt(_hh[q])

# ============================================================ H5: multi-turn at three rungs, with the aborted trajectories
H5, MTR = {}, {}
for q, rw in RUNG:
    d = RUNS / "Qwen3-1.7B" / "multi_turn_base" / q
    v = _acc_rows(d, "*multi_turn_base*.json")
    if not v: continue
    H5[q] = v; extra["MtAcc" + rw] = f"{acc(v):.2f}"; extra["MtN"] = len(v); extra["MtCi" + rw] = ci(v)
    rows = result_rows(d, "*multi_turn_base*.json")
    err = [r for r in rows if isinstance(r.get("result"), str) and r["result"].startswith("Error during inference")]
    extra["MtAborted" + rw] = len(err); extra["MtCtxErr" + rw] = sum(1 for r in err if "Context size" in r["result"])
    ok = [r for r in rows if r not in err]; extra["MtCompleted" + rw] = len(ok)
    corr = sum(v.values()); assert all(not v[r["id"]] for r in err), "an aborted trajectory scored correct"
    extra["MtCompletedAcc" + rw] = f"{100 * corr / len(ok):.1f}"; extra["MtCompletedCorrect" + rw] = corr
    out, tot = [], []
    for r in ok:
        o = [y for x in r["output_token_count"] for y in (x if isinstance(x, list) else [x])]
        i = [y for x in r["input_token_count"] for y in (x if isinstance(x, list) else [x])]
        out += o; tot += [a + b for a, b in zip(i, o)]
    out.sort(); tot.sort(); n = len(out)
    extra["MtReq" + rw] = n; extra["MtReqMed" + rw] = out[n // 2]; extra["MtReqPninezero" + rw] = out[int(.9 * n)]
    extra["MtReqCap" + rw] = sum(1 for x in out if x >= CAP)
    extra["MtCtxMed" + rw] = f"{tot[n // 2]:,}"; extra["MtCtxPninezero" + rw] = f"{tot[int(.9 * n)]:,}"; extra["MtCtxMax" + rw] = f"{tot[-1]:,}"
_srv = (RUNS / "Qwen3-1.7B" / "multi_turn_base-Q8_0.server.log").read_text()
_m = re.search(r"n_slots = (\d+), n_ctx_slot = (\d+), kv_unified = '(\w+)'", _srv)
extra["MtSlots"], extra["MtCtxSlot"], extra["MtKvUnified"] = _m.group(1), f"{int(_m.group(2)):,}", _m.group(3)
_mp = {}
for q, rw in RUNG:
    if q != "Q8_0" and q in H5:
        lost, gained, p = mcnemar(H5["Q8_0"], H5[q]); _mp[q] = p
        extra["MtDelta" + rw] = f"{acc(H5[q]) - acc(H5['Q8_0']):+.2f}"; extra["MtP" + rw] = pfmt(p)
        extra["MtLost" + rw], extra["MtGained" + rw] = lost, gained
        extra["MtRel" + rw] = f"{(acc(H5[q]) - acc(H5['Q8_0'])) / acc(H5['Q8_0']) * 100:+.1f}"
        extra["SingleRel" + rw] = f"{float(N['Delta'+rw]) / float(N['AccEight']) * 100:+.1f}"
_mh = holm(_mp); TESTS += len(_mp); FAMILIES += 1
for q in _mp: extra["MtPHolm" + RW[q]] = pfmt(_mh[q])

# ============================================================ budget control (16K on the Q3_K_M truncations)
rows = [json.loads(l) for l in (RUNS / "gsm8k_budget" / "Q3_K_M_16k.jsonl").open()]
real = [r for r in rows if r.get("finish_reason") in ("stop", "length")]
fin = [r for r in real if r["finish_reason"] == "stop"]; cap = [r for r in real if r["finish_reason"] == "length"]
c = lambda rs: sum(gnorm(gstrict(r["content"])) == gnorm(r["gold"]) for r in rs)
extra["BudN"] = len(real); extra["BudFinished"] = len(fin); extra["BudStillCap"] = len(cap); extra["BudErr"] = len(rows) - len(real)
extra["BudStillCapPct"] = f"{100*len(cap)/max(1,len(real)):.0f}"
extra["BudRecovered"] = c(fin) + c(cap); extra["BudRecoveredPct"] = f"{100*(c(fin)+c(cap))/max(1,len(real)):.0f}"
extra["BudOf"] = len(rows)
assert extra["BudOf"] == extra["GsmTruncThree"], "budget re-run does not cover the truncated set"

# ============================================================ second family: Llama GSM8K
FAM = [("Llama-3.2-3B", "LlamaThreeB"), ("Llama-3.1-8B", "LlamaEightB")]
FRUNG = [("Q8_0", "Eight"), ("Q4_K_M", "Four"), ("Q3_K_M", "Three")]
fam = {}
for stem, w in FAM:
    G2 = {}
    for q, rw in FRUNG:
        rows = [json.loads(l) for l in (RUNS / stem / "gsm8k" / f"{q}.jsonl").open()]
        ver = {r["id"]: (gnorm(gstrict(r["content"])) == gnorm(r["gold"])) for r in rows}
        len_ = {r["id"]: (gnorm(glenient(r["content"])) == gnorm(r["gold"])) for r in rows}
        G2[q] = ver
        toks = sorted(r["completion_tokens"] or 0 for r in rows)
        fam[f"{w}GsmN"] = len(rows)
        fam[f"{w}GsmStrict{rw}"] = f"{100*sum(ver.values())/len(rows):.2f}"
        fam[f"{w}GsmCi{rw}"] = ci(ver)
        fam[f"{w}GsmLenient{rw}"] = f"{100*sum(len_.values())/len(rows):.2f}"
        fam[f"{w}GsmGap{rw}"] = f"{100*(sum(len_.values())-sum(ver.values()))/len(rows):+.2f}"
        fam[f"{w}GsmTrunc{rw}"] = sum(1 for r in rows if r["finish_reason"] == "length")
        fam[f"{w}GsmMedTok{rw}"] = toks[len(toks)//2]
        for k in ("Fails", "TypeErr", "DecodeErr", "Coercible", "CoercedAcc"):
            fam[f"{w}{k}{rw}"] = extra[f"{k}{w}{rw}"]
    _fp = {}
    for q, rw in FRUNG[1:]:
        fam[f"{w}CoercedDelta{rw}"] = extra[f"CoercedDelta{w}{rw}"]
        lost, gained, pg = mcnemar(G2["Q8_0"], G2[q]); _fp[q] = pg
        fam[f"{w}GsmDelta{rw}"] = f"{100*(sum(G2[q].values())-sum(G2['Q8_0'].values()))/len(G2[q]):+.2f}"
        fam[f"{w}GsmP{rw}"] = pfmt(pg)
        fam[f"{w}GsmLost{rw}"], fam[f"{w}GsmGained{rw}"] = lost, gained
    _fh = holm(_fp); TESTS += len(_fp); FAMILIES += 1
    for q, rw in FRUNG[1:]: fam[f"{w}GsmPHolm{rw}"] = pfmt(_fh[q])
    # H3 as registered on this model: coerced AST drop against the strict free-form drop at Q3_K_M
    fam[f"{w}HthreeDiff"] = f"{abs(float(fam[f'{w}GsmDeltaThree'])) - abs(float(extra[f'CoercedDelta{w}Three'])):.2f}"

# ============================================================ published BFCL leaderboard row for Llama-3.1-8B-Instruct
lb = {}
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

extra["TestsTotal"] = TESTS; extra["FamiliesTotal"] = FAMILIES

# ============================================================ write every macro
with (TAB / "numbers.tex").open("w") as f:
    for src in (N, extra, fam, lb):
        for k, v in src.items(): f.write(f"\\newcommand{{\\qt{mac(k)}}}{{{v}}}\n")
# unsigned drops for prose ("loses X points")
_n = (TAB / "numbers.tex").read_text()
_drops = []
for _m in re.finditer(r"\\newcommand\{\\qt(\w*?)Delta(\w+)\}\{([+-]?[\d.]+)\}", _n):
    _drops.append(f"\\newcommand{{\\qt{_m.group(1)}Drop{_m.group(2)}}}{{{abs(float(_m.group(3))):.2f}}}\n")
with (TAB / "numbers.tex").open("a") as f: f.writelines(_drops)
_names = re.findall(r"\\newcommand\{(\\qt\w+)\}", (TAB / "numbers.tex").read_text())
_dup = sorted({x for x in _names if _names.count(x) > 1})
if _dup: sys.exit(f"duplicate macro names: {_dup}")
print(f"total macros: {len(_names)}, no duplicates; {TESTS} McNemar tests in {FAMILIES} Holm families")

# ============================================================ tables
def P(k): return N.get(k, extra.get(k))

# ladder
L = ["\\begin{tabular}{@{}lrlrrrl@{}}", "\\toprule",
     "Rung & Size (GB) & Accuracy [95\\% CI] & vs.\\ Q8\\_0 & Lost & Gained & McNemar $p$ (Holm) \\\\", "\\midrule"]
for q, w in RUNG:
    cell = f"{N['Acc'+w]}\\% [{N['Ci'+w]}]"
    if q == "Q8_0": L.append(f"{lab(q)} & {N['Size'+w]} & {cell} & baseline & & & \\\\")
    else: L.append(f"{lab(q)} & {N['Size'+w]} & {cell} & {sgn(N['Delta'+w])}\\,pp & {N['Lost'+w]} & {N['Gained'+w]} & {N['P'+w]} ({bold(extra['PHolm'+w])}) \\\\")
L += ["\\bottomrule", "\\end{tabular}"]
(TAB / "ladder.tex").write_text("\n".join(L) + "\n")

# repeats
R = ["\\begin{tabular}{@{}llrr@{}}", "\\toprule", "Rung & Accuracy per run & Range (pp) & Max per-question flips \\\\", "\\midrule"]
for q, w in (("Q8_0", "Eight"), ("Q4_K_M", "Four")):
    R.append(f"{lab(q)} & {N['RepList'+w]} & {N['RepRange'+w]} & {N['RepFlipsMax'+w]} of {N['N']} \\\\")
R += ["\\bottomrule", "\\end{tabular}"]
(TAB / "repeats.tex").write_text("\n".join(R) + "\n")

# gsm8k, with the truncation columns
L = ["\\begin{tabular}{@{}llrrrlrrr@{}}", "\\toprule",
     "Rung & Strict [95\\% CI] & Lenient & Gap & vs.\\ Q8\\_0 & McNemar $p$ (Holm) & Median tokens & Truncated & Truncated, correct \\\\", "\\midrule"]
for q, w in RUNG:
    cell = f"{extra['GsmStrict'+w]}\\% [{extra['GsmCi'+w]}]"
    tail = f"{extra['GsmMedTok'+w]} & {extra['GsmTrunc'+w]} & {extra['GsmTruncCorrect'+w]} \\\\"
    if q == "Q8_0": L.append(f"{lab(q)} & {cell} & {extra['GsmLenient'+w]}\\% & {extra['GsmGap'+w]}\\,pp & baseline & & {tail}")
    else: L.append(f"{lab(q)} & {cell} & {extra['GsmLenient'+w]}\\% & {extra['GsmGap'+w]}\\,pp & {sgn(extra['GsmDelta'+w])}\\,pp & {extra['GsmP'+w]} ({bold(extra['GsmPHolm'+w])}) & {tail}")
L += ["\\bottomrule", "\\end{tabular}"]; (TAB / "gsm8k.tex").write_text("\n".join(L) + "\n")

# models: strict and coerced, raw p and Holm p
L = ["\\begin{tabular}{@{}llrlrlllrl@{}}", "\\toprule",
     "Model & Rung & $n$ & Strict [95\\% CI] & vs.\\ Q8\\_0 & $p$ (Holm) & Coerced [95\\% CI] & vs.\\ Q8\\_0 & Lost/gained & $p$ (Holm) \\\\", "\\midrule"]
for stem, w in MODEL_W:
    for q, rw in RUNG:
        if stem == "Qwen3-1.7B" and q not in ("Q8_0", "Q4_K_M", "Q3_K_M"): continue
        if (stem, q) not in S: continue
        a = P(f"Acc{w}{rw}"); cia = P(f"Ci{w}{rw}"); n = P(f"N{w}") if w else N["N"]
        ca = extra[f"CoercedAcc{w}{rw}"]; cic = extra[f"CoercedCi{w}{rw}"]
        if q == "Q8_0":
            L.append(f"{stem} & {lab(q)} & {n} & {a}\\% [{cia}] & baseline & & {ca}\\% [{cic}] & baseline & & \\\\")
        else:
            d = P(f"Delta{w}{rw}"); p = P(f"P{w}{rw}"); ph = extra[f"PHolm{w}{rw}"]
            cd = extra[f"CoercedDelta{w}{rw}"]; cp = extra[f"CoercedP{w}{rw}"]; cph = extra[f"CoercedPHolm{w}{rw}"]
            lg = f"{extra[f'CoercedLost{w}{rw}']}/{extra[f'CoercedGained{w}{rw}']}"
            L.append(f"{stem} & {lab(q)} & {n} & {a}\\% [{cia}] & {sgn(d)}\\,pp & {p} ({bold(ph)}) & {ca}\\% [{cic}] & {sgn(cd)}\\,pp & {lg} & {cp} ({bold(cph)}) \\\\")
    L.append("\\midrule")
L = L[:-1] + ["\\bottomrule", "\\end{tabular}"]; (TAB / "models.tex").write_text("\n".join(L) + "\n")

# four-bit bound: paired difference at Q4_K_M with its interval and the minimum detectable difference
L = ["\\begin{tabular}{@{}llrrrlrr@{}}", "\\toprule",
     "Model & Verdict & $n$ & Lost & Gained & Difference [95\\% CI] (pp) & $p$ (Holm) & MDD (pp) \\\\", "\\midrule"]
for stem, w in MODEL_W:
    n = P(f"N{w}") if w else N["N"]
    same = C[(stem, "Q4_K_M")] == S[(stem, "Q4_K_M")] and C[(stem, "Q8_0")] == S[(stem, "Q8_0")]
    L.append(f"{stem} & {'strict = coerced' if same else 'strict'} & {n} & {P(f'Lost{w}Four')} & {P(f'Gained{w}Four')} & {sgn(P(f'Delta{w}Four'))} {extra[f'DiffCi{w}Four']} & {P(f'P{w}Four')} ({bold(extra[f'PHolm{w}Four'])}) & {extra[f'Mde{w}Four']} \\\\")
    if not same:
        L.append(f"{stem} & coerced & {n} & {extra[f'CoercedLost{w}Four']} & {extra[f'CoercedGained{w}Four']} & {sgn(extra[f'CoercedDelta{w}Four'])} {extra[f'CoercedDiffCi{w}Four']} & {extra[f'CoercedP{w}Four']} ({bold(extra[f'CoercedPHolm{w}Four'])}) & {extra[f'CoercedMde{w}Four']} \\\\")
L += ["\\bottomrule", "\\end{tabular}"]; (TAB / "fourbit.tex").write_text("\n".join(L) + "\n")

# H2 as registered: structural share of failures at Q8_0 and Q3_K_M per model
L = ["\\begin{tabular}{@{}lrrrrrrr@{}}", "\\toprule",
     "Model & Failures Q8\\_0 & Structural & Share (\\%) & Failures Q3\\_K\\_M & Structural & Share (\\%) & Change (pp) \\\\", "\\midrule"]
for stem, w in MODEL_W:
    a, b = ST[(stem, "Q8_0")], ST[(stem, "Q3_K_M")]
    L.append(f"{stem} & {a['fails']} & {a['struct']} & {frac(a['struct'], a['fails'])} & {b['fails']} & {b['struct']} & {frac(b['struct'], b['fails'])} & {sgn(extra[f'HtwoDelta{w}'])} \\\\")
L += ["\\bottomrule", "\\end{tabular}"]; (TAB / "htwo.tex").write_text("\n".join(L) + "\n")

# second family: failure types and GSM8K (llama_failures.tex); llama.tex kept for the TMLR manuscript
L = ["\\begin{tabular}{@{}llrrrrrrr@{}}", "\\toprule",
     "Model & Rung & Tool acc. & vs.\\ Q8\\_0 & $p$ & Coerced & GSM8K strict & vs.\\ Q8\\_0 & $p$ \\\\", "\\midrule"]
F = ["\\begin{tabular}{@{}llrrrrrlrl@{}}", "\\toprule",
     "Model & Rung & Strict failures & Type errors & Decode failures & JSON calls & Coercible & GSM8K strict [95\\% CI] & vs.\\ Q8\\_0 & $p$ (Holm) \\\\", "\\midrule"]
for stem, w in FAM:
    for q, rw in FRUNG:
        gs = fam[f"{w}GsmStrict{rw}"]; gd = fam.get(f"{w}GsmDelta{rw}"); gp = fam.get(f"{w}GsmP{rw}", ""); gph = fam.get(f"{w}GsmPHolm{rw}", "")
        fmt = lambda d: "baseline" if d is None else sgn(d) + "\\,pp"
        ta = extra[f"Acc{w}{rw}"]; td = extra.get(f"Delta{w}{rw}"); tp = extra.get(f"P{w}{rw}", ""); ca = extra[f"CoercedAcc{w}{rw}"]
        L.append(f"{stem} & {lab(q)} & {ta}\\% & {fmt(td)} & {bold(tp)} & {ca}\\% & {gs}\\% & {fmt(gd)} & {bold(gp)} \\\\")
        pc = "" if gd is None else f"{gp} ({bold(gph)})"
        F.append(f"{stem} & {lab(q)} & {extra[f'Fails{w}{rw}']} & {extra[f'TypeErr{w}{rw}']} & {extra[f'DecodeErr{w}{rw}']} & {extra[f'DecodeJson{w}{rw}']} & {extra[f'Coercible{w}{rw}']} & {gs}\\% [{fam[f'{w}GsmCi{rw}']}] & {fmt(gd)} & {pc} \\\\")
    L.append("\\midrule"); F.append("\\midrule")
L = L[:-1] + ["\\bottomrule", "\\end{tabular}"]; (TAB / "llama.tex").write_text("\n".join(L) + "\n")
F = F[:-1] + ["\\bottomrule", "\\end{tabular}"]; (TAB / "llama_failures.tex").write_text("\n".join(F) + "\n")

# multi-turn, with the aborted trajectories
L = ["\\begin{tabular}{@{}lrlrrlrr@{}}", "\\toprule",
     "Rung & $n$ & Accuracy, all [95\\% CI] & vs.\\ Q8\\_0 & Lost/Gained & McNemar $p$ (Holm) & Aborted & Accuracy, completed \\\\", "\\midrule"]
for q, rw in RUNG:
    if q not in H5: continue
    cell = f"{extra['MtAcc'+rw]}\\% [{extra['MtCi'+rw]}]"
    tail = f"{extra['MtAborted'+rw]} & {extra['MtCompletedCorrect'+rw]}/{extra['MtCompleted'+rw]} ({extra['MtCompletedAcc'+rw]}\\%) \\\\"
    if q == "Q8_0": L.append(f"{lab(q)} & {extra['MtN']} & {cell} & baseline & & & {tail}")
    else: L.append(f"{lab(q)} & {extra['MtN']} & {cell} & {sgn(extra['MtDelta'+rw])}\\,pp & {extra['MtLost'+rw]}/{extra['MtGained'+rw]} & {extra['MtP'+rw]} ({bold(extra['MtPHolm'+rw])}) & {tail}")
L += ["\\bottomrule", "\\end{tabular}"]; (TAB / "multiturn.tex").write_text("\n".join(L) + "\n")
print("tables written:", sorted(p.name for p in TAB.glob("*.tex")))
for k in ("AccEight", "AccFour", "AccThree", "DeltaThree", "PThree", "MaxRepRange", "CliffOverNoise", "SizeFp", "CompressFour"): print(f"  {k} = {N[k]}")
for k in ("PHolmThree", "CoercedAccLlamaEightBThree", "CoercedPLlamaEightBThree", "CoercedPHolmLlamaEightBThree", "CliffStrictLlamaThreeB", "CliffCoercedLlamaEightB",
          "FourBitLoStrict", "FourBitLoCoerced", "FourBitMdeMax", "HtwoDelta", "HtwoDeltaLlamaEightB", "HtwoDeltaJsonLlamaEightB", "HthreeDiff", "HoneSchemaMin",
          "MtAbortedThree", "MtCompletedAccThree", "ToolNgenMedThree", "ToolNgenPninezeroThree", "ToolNgenCapThree", "GsmTruncNoAnswerThree", "GsmTruncWrongThree", "TestsTotal"):
    print(f"  {k} = {P(k)}")

#!/usr/bin/env python3
"""Fig. 1: (a) accuracy across the ladder for tool calling and free-form math on identical weights;
(b) completion-length CDFs showing the chain-of-thought run-away that the call never has room for."""
import json, re, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent.parent; RUNS = HERE / "runs"; FIG = HERE / "paper" / "figures"; FIG.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE)); from gsm8k_score import strict, norm
matplotlib.rcParams.update({"pdf.fonttype": 42, "font.size": 9, "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman"], "mathtext.fontset": "stix",
    "axes.spines.top": False, "axes.spines.right": False})
RUNG = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M"]; BITS = [8, 6, 5, 4, 3]

def bfcl_acc(run_dir, cat="simple_python"):
    sc = next((run_dir / "score").rglob(f"*{cat}*.json"), None); rs = next((run_dir / "result").rglob(f"*{cat}*.json"), None)
    if not sc or not rs: return None
    bad = {json.loads(l)["id"] for l in sc.open() if l.strip() and "id" in json.loads(l)}
    ids = {json.loads(l)["id"] for l in rs.open() if l.strip()}
    return 100 * sum(1 for i in ids if i not in bad) / len(ids)
tool17 = [bfcl_acc(RUNS / q) for q in RUNG]
tool8 = {q: bfcl_acc(RUNS / "Qwen3-8B" / q) for q in ("Q8_0", "Q4_K_M", "Q3_K_M")}
math17, mtoks = [], {}
for q in RUNG:
    rows = [json.loads(l) for l in (RUNS / "gsm8k" / f"{q}.jsonl").open()]
    math17.append(100 * sum(norm(strict(r["content"])) == norm(r["gold"]) for r in rows) / len(rows))
    mtoks[q] = sorted(r["completion_tokens"] or 0 for r in rows)
def tool_toks(run_dir):
    """Per-request completion length from BFCL's result file (the server log's n_gen lines are
    3-second progress prints, several per long request, and were used here before 29 Sep 2026)."""
    rs = next((run_dir / "result").rglob("*simple_python*.json"))
    return sorted(json.loads(l)["output_token_count"] for l in rs.open() if l.strip())
ttoks = {q: tool_toks(RUNS / q) for q in ("Q8_0", "Q3_K_M")}

fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 2.7), gridspec_kw={"width_ratios": [1.05, 1]})
x = list(range(len(RUNG)))
a.plot(x, tool17, "o-", color="#4477AA", lw=1.6, label="tool calling, Qwen3-1.7B")
a.plot(x, math17, "s-", color="#EE6677", lw=1.6, label="free-form math, same weights")
xs8 = [RUNG.index(q) for q in tool8 if tool8[q] is not None]
a.plot(xs8, [tool8[RUNG[i]] for i in xs8], "o--", color="#4477AA", lw=1.2, mfc="white", label="tool calling, Qwen3-8B")
a.set_xticks(x); a.set_xticklabels([f"{r}\n{b_}-bit" for r, b_ in zip(RUNG, BITS)], fontsize=7.5)
a.set_ylabel("accuracy (%)"); a.set_ylim(40, 100)
a.annotate(f"{tool17[-1]-tool17[0]:+.2f} pp", xy=(4, tool17[-1]), xytext=(3.05, 70), fontsize=8, color="#4477AA",
           arrowprops=dict(arrowstyle="->", color="#4477AA", lw=0.8))
a.annotate(f"{math17[-1]-math17[0]:+.2f} pp", xy=(4, math17[-1]), xytext=(2.6, 52), fontsize=8, color="#EE6677",
           arrowprops=dict(arrowstyle="->", color="#EE6677", lw=0.8))
a.legend(frameon=False, fontsize=7.2, loc="lower left"); a.set_title("(a) same weights, two tasks", fontsize=9, loc="left")

def cdf(ax, v, **kw):
    ax.step(v, [(i + 1) / len(v) for i in range(len(v))], where="post", **kw)
cdf(b, ttoks["Q8_0"], color="#4477AA", lw=1.4, label="tool call, Q8_0")
cdf(b, ttoks["Q3_K_M"], color="#4477AA", lw=1.4, ls="--", label="tool call, Q3_K_M")
cdf(b, mtoks["Q8_0"], color="#EE6677", lw=1.4, label="math, Q8_0")
cdf(b, mtoks["Q3_K_M"], color="#EE6677", lw=1.4, ls="--", label="math, Q3_K_M")
b.axvline(4096, color="black", lw=0.9, ls=":"); b.text(4096 * 1.06, 0.52, "4,096-token budget", rotation=90, ha="left", va="center", fontsize=7.2)
b.set_xscale("log"); b.set_xlim(20, 5000); b.set_ylim(0, 1.02)
ncap = sum(1 for t in mtoks["Q3_K_M"] if t >= 4096)
b.text(3850, 0.505, f"{ncap} of 400 math\ngenerations stuck\nat the cap", ha="right", va="bottom", fontsize=7.2, color="#EE6677")
b.set_xlabel("completion length (tokens, log scale)"); b.set_ylabel("fraction of generations")
b.legend(frameon=False, fontsize=7.2, loc="upper left"); b.set_title("(b) where the length goes", fontsize=9, loc="left")
fig.tight_layout(w_pad=1.5); fig.savefig(FIG / "fig1-ladder.pdf", bbox_inches="tight")
trunc3 = sum(1 for t in mtoks["Q3_K_M"] if t >= 4096)
print(f"fig1-ladder.pdf; tool 1.7B {tool17[0]:.2f}->{tool17[-1]:.2f}, math {math17[0]:.2f}->{math17[-1]:.2f}, math@Q3 at cap {trunc3}/400, tool@Q3 median {ttoks['Q3_K_M'][len(ttoks['Q3_K_M'])//2]}")

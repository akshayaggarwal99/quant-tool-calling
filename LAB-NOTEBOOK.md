# Quant-tools lab notebook

## 18 Sep 2026 — day 1

### Novelty checks (the items that could kill the project)

- **k-quant ladder x tool calling: gap CONFIRMED OPEN.** Closest work is arXiv 2601.14277,
  *Which Quantization Should I Use?*, which quantizes Llama-3.1-8B-Instruct into 13 GGUF formats
  and scores GSM8K, HellaSwag, IFEval, MMLU, TruthfulQA and WikiText-2 perplexity. Full-text read
  found no tool calling, function calling, agentic, structured-output or schema-compliance
  evaluation anywhere. Their conclusion asks for exactly what we do: "Future work should extend the
  same protocol across additional model families and sizes."
- **Lotfi et al. 2606.00206 read in full.** Uses GPTQ/AWQ/FlatQuant, not llama.cpp k-quants, on
  GSM8K, MATH-500, AIME-120, LiveCodeBench, GPQA-Diamond. No tool calling. Their overthinking
  categorisation, which carries the 52% figure, uses GPT-5 as an LLM judge. Ours uses deterministic
  AST matching and has no judge anywhere.
- Multilingual quantization was dropped before any work: already covered by three papers with
  contested findings.

### Environment

Machine is an M1 Max with 64 GB and 1.3 TB free, not the 16 GB M1 Pro assumed when planning. That
puts 32B models in range, so the size span can match Lotfi et al.

- ollama 0.33.2, serving an OpenAI-compatible API on 11434
- llama.cpp 0.4.1 via Homebrew: llama-quantize, llama-server
- bfcl-eval 2026.3.23 in .venv. Needed `soundfile` installed by hand; the package imports
  qwen_agent, which imports it unconditionally.

### Pipeline, proven end to end

BFCL's OSS handler honours `LOCAL_SERVER_ENDPOINT` / `LOCAL_SERVER_PORT`, so any OpenAI-compatible
server works with `--skip-server-setup`. BFCL sends the model id `Qwen/Qwen3-1.7B`, so the server
must answer to that name; `llama-server --alias` does it.

First real number: **Qwen3-1.7B-FC, simple_python, 91.08%** on 213 entries through Ollama's default
quantization. Generate and evaluate both work.

### Quantization ladder

Built from one FP16 GGUF source (Ollama's `qwen3:1.7b-fp16` blob, 3.8 GB) with `llama-quantize`,
so the ladder is controlled by construction:

| rung | size |
|---|---|
| Q8_0 | 2.0 GB |
| Q6_K | 1.6 GB |
| Q5_K_M | 1.4 GB |
| Q4_K_M | 1.2 GB |
| Q3_K_M | 1.0 GB |

Ollama's library only publishes q4_K_M, q8_0 and fp16 for this model, which is why the ladder is
built rather than pulled.

### Running

`run_ladder.sh` serves each rung with llama-server under the alias BFCL expects, runs generate and
evaluate, and archives `result/` and `score/` to `runs/<rung>/`. Only the weights change between
rungs. Started on simple_python at 15:4x.

Measured throughput: 4 parallel slots, ~35 tok/s generation per slot, ~650 tok/s prompt eval,
roughly 15 s per entry wall clock. About 100 minutes per rung for 400 entries, so ~8.5 hours for
the five-rung ladder. Qwen3 emits thinking traces, which is most of the per-entry cost.

### Open

- Ladder run to finish, then `analyze.py` for the deployment table.
- Free-form control arm (the H3 extraction comparison) not yet built.
- Larger models not yet pulled; qwen3:32b is already on the machine at 20 GB.

### GCP evaluated and rejected for this workload (18 Sep, measured not assumed)

Quota, checked on both research projects:

| project | credits | GPU quota | CPU quota |
|---|---|---|---|
| project-ff735d80 (himanshi) | the free-trial balance | 0 | 32 vCPU |
| boxed-bench-2026 (akshay.iitr) | paid card | 1 | 32 vCPU |

The credits and the one GPU are on different projects, so a GPU run would charge the card rather
than spend credits. Credits mean CPU only.

Benchmarked rather than guessed. Started sf-swe2 (n2-standard-8, Cascade Lake, AVX-512), ran
llama-bench on Qwen3-1.7B-Q8_0 under the official llama.cpp image, then stopped the instance.
Note c3 capacity was unavailable in us-east4-a and n2d in us-central1-a, so zone capacity is an
ongoing constraint on this account.

| | prompt eval | generation |
|---|---|---|
| GCP n2-standard-8, CPU, 8 threads | 109.6 tok/s | 22.0 tok/s |
| Mac M1 Max, Metal, 4 slots | ~650 tok/s | ~35 tok/s per slot, ~140 aggregate |

One Mac is roughly six times one instance on both axes. Spending the entire 32 vCPU quota on four
instances gives about 88 tok/s of generation, still below the single Mac, and prompt eval matters
here because tool-calling prompts carry full function schemas.

Decision: run everything on the Mac. GCP is not worth the credits or the orchestration for this
workload. Revisit only if GPU quota is granted on the project that holds the credits.
Test cost about ten cents.

### First complete rung

**Q8_0, simple_python, 400/400 entries, 91.75%.** Roughly 100 minutes, matching the estimate.
Q6_K running next.

### Ladder complete, repeats complete, scaffold drafted (18 Sep, evening)

Full ladder and both repeat arms finished. Analysis in out/day1-findings.md. Headline for
Qwen3-1.7B on simple_python: flat Q8_0 through Q4_K_M (Q4 vs Q8 +0.25 pp, McNemar p=1.000), cliff
at Q3_K_M (-4.75 pp, p=0.004). Same-weights repeats move at most 0.50 pp and flip at most 4 of 400
questions, so the cliff is ~10x instrument noise. H1 is looking unsupported: the tool-calling floor
sits where the published free-form floor sits. Not yet a fair test until the free-form arm runs on
these weights.

Free-form arm launched: 400 GSM8K test questions (seed 42) through the same server alias, all five
rungs, full generations logged for re-scoring under strict and lenient extractors. ~110 min per
rung, overnight.

Paper scaffold at paper/main.tex, 5 pages, 12 red BLOCKED slots for unmeasured arms, every
number a macro from analysis/paper_numbers.py. Bib has 9 entries; kurt2026quant, lotfi2026overthink
and bfcl2025 verified against source pages. Caught and fixed my own error: 2601.14277 is single-
author (Uygar Kurt), not "Wang et al." as I had written in the prereg from memory.

Gotcha: a script named numbers.py shadows the stdlib module that `statistics` imports. Renamed
to paper_numbers.py.

Repo initialised and tagged prereg-v1.

### Caught a strawman extractor (18 Sep, before any rung scored)

First 59 GSM8K generations at Q8_0: my strict regex ("The answer is N" only) scored 31/59, lenient
52/59. All 21 misses were `\boxed{N}` under a "Final Answer" heading, which is the commit format
reasoning models actually emit despite the prompt. Reporting that gap would have been reporting my
regex. Strict now accepts any explicit commitment ("The answer is", "#### N", \boxed{N}); lenient is
last-number. Rules recorded in the prereg before scoring. Whatever gap remains after this is real.

Queue launched behind the GSM8K arm: Qwen3-4B (3 rungs, n=400), Qwen3-8B (3 rungs, n=200), H4 logit
penalty on 1.7B at Q4/Q3, Qwen3-14B (3 rungs, n=200). Rough serial estimate ~2 days on the Mac.
DeepSeek-R1-Distill and Llama-3.1 have no FP16 on Ollama; deferred as a stretch arm needing an HF
conversion.

### Two bugs caught in the first hour of the free-form arm (18 Sep, late)

1. `llama-server -c 8192` with four slots under unified KV is a shared 8,192-token budget. Four
   concurrent reasoning traces overflowed it, the server returned 500 "Context size has been
   exceeded", and ThreadPoolExecutor.map re-raised it and killed the generator at item 59, 28, 28.
   Fix: per-item try/except recording an `error` row so a run always completes, and `-c 32768` in
   both runners. Partial rung files deleted; arm relaunched from Q8_0.
2. BFCL has no local FC entry for the original Qwen3-4B, only Qwen3-4B-Instruct-2507, a different
   lineage. Dropped 4B rather than confound the within-family size comparison. Span is now 1.7B,
   8B (n=200), 14B (n=200). H4 runs between 8B and 14B.

### Paused for the author's RAM; scheduled to resume 23:00 (18 Sep, ~19:15)

All jobs stopped, 16 GB returned. Generator made resumable (append mode, skips finished ids) so the
partial Q6_K rung (150/400) continues rather than restarts. New sequential driver run_all.sh runs the
arms in paper-priority order, GSM8K -> H4 -> 8B -> multi-turn -> 14B, each to its own log so the
skip logic and wake-up watchers still work. Launched via a sleep-until-23:00 wrapper under
caffeinate -i so the Mac does not idle-sleep mid-run.

Observed rate on the free-form arm is ~7 items/min, faster than the 110 min/rung estimate.

Preliminary, Q8_0 GSM8K, n=400: strict 86.25%, lenient 86.50%, gap +0.25 pp. With a fair strict
extractor the parser effect is a quarter of a point. 28 of 400 hit the 4,096-token cap still inside
the thinking trace and produced no visible answer (25 empty contents); they score as failures under
both extractors, which is the right call, and the count is reported per rung as GsmTrunc.

## 19 Sep 2026 — overnight campaign

Driver fired 23:00:03. GSM8K (5 rungs), H4 (2 rungs) and Qwen3-8B (3 rungs, n=200) all finished by
04:55; multi-turn on Q3_K_M running at 09:xx; 14B queued.

### Free-form control (GSM8K, n=400, strict/lenient)
Q8_0 86.25/86.50, Q6_K 86.50/86.50, Q5_K_M 88.75/89.25, Q4_K_M 85.50/85.75, Q3_K_M 46.75/46.75.
Q3_K_M: -39.50 pp vs Q8_0, McNemar p<0.0001; 213 of 400 hit the 4,096-token cap still thinking,
median completion = cap. Extractor gap 0.00-0.50 pp at every rung.

### Verdicts
- H1 (schema breaks first): NOT SUPPORTED, and reversed. Both floors sit between Q4_K_M and Q3_K_M
  on the same weights, but the free-form drop is 39.5 pp against 4.75 pp for tool calling. The
  schema is the more robust output, not the more fragile one.
- H3 (extractor bounds free-form drop): NULL. With a fair strict extractor the gap is at most
  0.50 pp. Lotfi et al.'s failures are not a parsing artifact in our data; at Q3_K_M they are
  chain-of-thought explosions that never produce an answer.
- 8B (n=200): Q8_0 95.50, Q4_K_M 96.50, Q3_K_M 96.50. No cliff. The 3-bit cliff at 1.7B is gone at
  8B (p=0.688). Floor moves down with size, now shown for tool calling.
- H4 (marker logit penalty, -2.0 on 8 tokens): exactly zero effect at Q4 (92.00 -> 92.00, 2 lost/
  2 gained) and Q3 (87.00 -> 87.00). NULL. Tool-call outputs barely emit the marker tokens.
- H5 (multi-turn, partial n=200): Q8_0 17.00, Q4_K_M 13.50, -3.50 pp, p=0.230, relative -20.6% vs
  single-turn +0.3%. Direction matches H5, not significant at this n. Q3_K_M pending.

Title must change: the pre-registered working title asserts the opposite of the result.

### Stopped for thermal load; moved to bounded nightly windows (19 Sep, ~10:30)

Author reported the Mac running hot. All compute stopped; one orphaned llama-server (the multi-turn
Q3_K_M rung, left behind when run_model.sh was killed) had to be found and killed by path. Note for
next time: kill llama-server first, then the drivers, or the server outlives them.

nightly.sh now runs run_all.sh only from 23:00 for 5 h (START_H / HOURS env), hard-stopped by
`timeout`, then kills any server. Every arm is resumable, so each night resumes where the last was
cut. Remaining: multi-turn Q3_K_M (was mid-rung), the 16K-budget control on the 213 truncated
Q3_K_M math items (folded inline into run_all.sh after multi-turn), then Qwen3-14B.

Figure 1 added (analysis/figure.py -> paper/figures/fig1-ladder.pdf): both tasks on one axis plus
completion-length CDFs. This is the figure that carries the paper.

Second family: bartowski publishes DeepSeek-R1-Distill-Qwen-1.5B-f16.gguf, but BFCL's config has no
R1-Distill model id string under any naming I tried; the deepseek_reasoning handler exists. Needs a
config entry to be added or found before it is feasible. Deferred.

## 20 Sep 2026

### The nightly window never fired, and the campaign ran during the day instead
nightly.sh used a shell `sleep` until 23:00. The Mac was asleep at 23:00 Sat (pmset log shows it
sleeping from ~21:39 with only dark wakes), and a sleeping shell does not count down, so the window
slid to the next real wake: 13:03 Sun, when the author was using the machine. It ran the multi-turn
Q3_K_M rung to completion (13:03-16:16) and 16 items of the budget control before I killed it at
19:34. This is the exact heat the schedule was meant to avoid. Replaced with a launchd
StartCalendarInterval job at 23:00 plus a pmset repeat wake at 22:58, so the machine wakes first
and the job fires on the clock rather than on a sleeping process.

## 21 Sep 2026

### Second scheduler failure: launchd fired on time and the script died on line 8
The Mac was awake and launchd ran nightly.sh at 23:00:00 exactly. It exited in the same second with
`timeout: command not found`. Homebrew's coreutils provides `timeout` at /opt/homebrew/bin, but launchd
starts scripts with a bare system PATH that does not include it. Fix: export PATH at the top of
nightly.sh, plus a hand-rolled watchdog fallback if gtimeout is ever absent. Verified the bounded
branch kills a process on schedule (exit 124). Reloaded the job. 14B FP16 pulled during the day so
the download does not consume the window. Lesson: anything launchd runs needs an explicit PATH.

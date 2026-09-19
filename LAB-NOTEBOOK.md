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

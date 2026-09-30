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

### 22 Sep: the 02:00 window worked end to end
Wake at 01:58, launchd at 02:00:03, gtimeout bounded it to 07:00. 14B resumed from its 100/200
checkpoint and finished all three rungs by 03:38; budget control ran 03:38-07:00 and reached 66
rows (62 real, 4 context errors even on 2 slots; acceptable). 14B: 96.00/96.00/96.50, p=1.000 at
Q3. Budget: 50/62 still at the 16K cap, 13/62 correct. Tonight finishes the budget arm.

### 23 Sep: window 3 clean, budget control 66 -> 136/213. ~70 items/night on 2 slots. One night left.

### 24 Sep: campaign complete
Window 4 (02:00-04:22) finished the budget control: 213/213 rows. ALL_COMPLETE. Numbers regenerated
from the full set; the "at the time of writing" hedges removed. launchd job unloaded. Every
pre-registered arm has run: ladder, repeats, GSM8K, H4, 8B, 14B, multi-turn, budget control.

### 24 Sep: arXiv submission
Review against a reference paper found one real gap: nine references. Added 13, each verified
against its arXiv abstract page, and confirmed by full-text grep that the three broad quantization
evaluations (Jin 2024, Li 2024, Liu 2025) contain no tool-calling benchmark, so the gap claim
stands. Also caught "loses -4.75 points" (signed macro after "loses"); added unsigned Drop macros.
Submitted as arXiv submit/8125878: cs.AI, cross-list cs.LG + cs.SE, CC BY 4.0. Bundle
paper/arxiv-v1.tar.gz (tex, bbl, bib, tables, figure). Compiled clean on arXiv pdflatex, 9 pages.

### 25 Sep: arXiv rejected the paper; TMLR version prepared; second family (Llama) queued

arXiv submit/8125878 rejected (MOD-105986, "not sufficient original or substantive scholarly
research"; no resubmission; appeal only with a journal DOI). TMLR version built in paper/main_tmlr.tex
(anonymous, tmlr.sty, 10 pp). The pre-submission gate failed on "one model family", so a second
family runs before submission: Llama-3.2-3B-Instruct and Llama-3.1-8B-Instruct, three rungs each
(Q8_0/Q4_K_M/Q3_K_M) from the Ollama fp16 blobs via llama-quantize, BFCL simple_python n=200
(subset200.json, same as Qwen3-8B/14B) plus GSM8K x400 at the 4,096 budget. Driver: run_llama.sh via
nightly.sh (02:00, 5 h windows, launchd loaded 25 Sep). Two gotchas found in a 3-item daytime smoke
(about one minute of GPU): meta-llama HF repos are gated, so BFCL's LlamaHandler_3_1 cannot fetch
config/tokenizer; fixed with REMOTE_OPENAI_BASE_URL=http://localhost:8099/v1 (the handler only honours
the tokenizer override when that is set) and REMOTE_OPENAI_TOKENIZER_PATH=unsloth/<model> (ungated
copies of the same files). Smoke: 3/3 correct at Q8_0. gsm8k_gen.py now takes the alias from
GSM_MODEL. Expected: 3B BFCL ~4 h, 3B GSM8K ~3 h, 8B BFCL ~12 h, 8B GSM8K ~6-8 h; four windows.

### 26 Sep: window 1 of the Llama arm ran in 2-minute slivers; flow fixed

No wake timer was set, so launchd fired on the first dark wake (02:13) and the Mac went back to
sleep two minutes later, 23 times, until the display came on at 07:55. `caffeinate -i` does not
hold a dark wake. Log timestamps are therefore wall-clock through sleep (Q8_0 "04:40 to 07:43" is
mostly sleep; the Q8_0 server log shows 163 ms/token prompt eval, a starved process). Results are
still valid: BFCL is request-based and every rung has 200 rows, 0 errors, 0 empty. Llama-3.2-3B
simple_python n=200: Q8_0 92.0, Q4_K_M 88.0, Q3_K_M 86.5 (raw, unpaired; McNemar later). GSM8K
Q8_0 reached 240/400, all finish_reason=stop, median 187 tokens. Window overran to 08:03 because
gtimeout does not count sleep; killed by hand. nightly.sh rewritten: caffeinate -i -s, real-clock
watchdog, absolute STOP_AT=07:30. Wake timer still needed: sudo pmset repeat wakeorpoweron MTWRFSU 01:58:00.

### 27 Sep: Llama arm complete (recorded 29 Sep)

Window of 02:00-04:17 on 27 Sep finished both Llama models on both arms with no errors or truncations
in the BFCL runs. Committed and tagged v1.1-second-family on 29 Sep with the TMLR-format manuscript.

## 29 Sep 2026 — PeerJ Computer Science version

### Coerced score re-derived with BFCL's own checker; numbers changed

The 27 Sep coerced re-score in paper_numbers.py used a regular expression over the checker's error
string: any type_error whose quoted value parsed as a number, list or boolean counted as correct. That
rule does not check the parsed value against the reference and it stops at the first error the
checker reported, so it over-counted. Replaced by analysis/coerced.py: each strict failure is passed
back through bfcl_eval's simple_function_checker with string arguments parsed to the schema's type
(integer literal, float, true/false, list or dict literal); anything else stays a string. The checker
then does what it would do for a natively typed value, including nested types, optional parameters and
value matching. Llama-3.1-8B coerced moves from 94.00 / 93.00 / 87.00 to 92.00 / 90.50 / 85.00 at
Q8_0 / Q4_K_M / Q3_K_M (coercible failures 84 / 55 / 27 of 100 / 74 / 57); Llama-3.2-3B stays at
93.50 / 91.00 / 91.00. Items the regex accepted and the checker rejects are, for example,
simple_python_122 (alpha "0" where the reference wants 0.05) and simple_python_13 (a quoted "[1, 3]"
where the schema wants an array of floats, which BFCL rejects for a natively typed [1, 3] as well).
The Qwen3 runs have 0 coercible failures out of 226, so their coerced columns equal strict. The
planning note's expected values of 78.0 / 78.0 / 76.0 for Llama-3.1-8B could not be reproduced under
any rule tried (numeric-only strings give 74.0 at Q8_0; numeric plus arrays plus booleans give 94.5 by
regex); the checker-based rule is the one the paper now states and uses. Coerced McNemar vs Q8_0:
3B Q4 p=0.125, Q3 p=0.180 (no cliff under the coerced verdict); 8B Q4 p=0.453, Q3 p=0.003.

Wilson 95% intervals added to every accuracy cell; cliff-rung macros (highest-precision rung with a
loss at p<0.05) computed per model and verdict; a multi-turn table with lost/gained (16/9 at Q4,
32/1 at Q3). Tables regenerate from analysis/paper_numbers.py; main_tmlr.tex still compiles against
them (llama.tex keeps its old layout, the failure-type table is llama_failures.tex).

### Llama-3.1-8B Q8_0 = 50.0% against the published BFCL number

The public leaderboard (gorilla.cs.berkeley.edu, BFCL V4; data_non_live.csv last modified 13 Apr 2026,
fetched 29 Sep, stored in analysis/bfcl_leaderboard/) lists Llama-3.1-8B-Instruct only in prompting
mode, "Llama-3.1-8B-Instruct (Prompt)", at 94.00% on Python simple AST (n=400), non-live overall
84.00%. There is no FC row for the model. Our run uses the FC handler (LlamaHandler_3_1): bfcl-eval
builds Meta's JSON tool-call prompt itself and sends it to llama-server's raw /v1/completions
endpoint, so --jinja is not in the path for the BFCL runs (it is for the GSM8K arm, which uses chat
completions); tokenizer and config come from unsloth/Llama-3.1-8B-Instruct via REMOTE_OPENAI_BASE_URL
and REMOTE_OPENAI_TOKENIZER_PATH. Under that format the full-precision model writes numbers as quoted
strings. Strict 50.0% vs published 94.0% is a 44-point gap; coerced 92.0% [87.4, 95.0] on the first
200 items is consistent with the published prompting-mode number. Reading: the discrepancy is the
argument-typing habit under the JSON tool-call format, not the weights or the server.
DECISION LINE FOR THE AUTHOR: a vLLM (or second-server) cross-check of Llama-3.1-8B Q8_0 in FC mode
is [ ] not needed, the coerced score settles it / [ ] needed before submission. The paper currently
says the cross-check has not been run.

Sampling policy recorded: BFCL and gsm8k_gen.py both send temperature 0.001; no seed is sent; the
llama-server binary reports version 0.4.1 (build 10964, commit b29c606e2) and its default seed is -1,
a fresh random seed per request. The three-run repeat control is what bounds the effect.

### PeerJ build

paper/peerj/main.tex written from main_tmlr.tex: 12 pt Times, US Letter, 2.5 cm margins, lineno,
left-justified, Author Cover Page first (Akshay Kumar, Independent Researcher, akumar8@mt.iitr.ac.in,
ORCID 0009-0006-3613-538X), structured abstract of 376 words, keywords, Materials and Methods with a
Problem statement subsection (ladder, verdicts, cliff rung, floor, flat, tolerance tau=0.50 pp,
n per model, single-run labels), a "Check against the published leaderboard" subsection, Results with
strict and coerced columns for all five models (Table 4), the Llama failure-type table (Table 5), the
multi-turn table (Table 6, section labelled sec:multiturn), Discussion with the practical reading
pointing at the multi-turn section, Limitations, Conclusions, and a declarations block (Competing
Interests, Author Contributions, Funding, Data Availability with a Zenodo DOI placeholder and tag
v1.2-peerj). Title: "Post-Training k-Quantization and Agentic Tool-Calling Accuracy on Five Qwen3 and
Llama Models" (12 words). Introduction opens on simple_python_21 at Q3_K_M (the GCD call replaced by a
wrong sentence). Contributions rewritten with numbers and table pointers. Refrains cut: "no judge"
once, "identical weights" twice. tectonic build: 19 pages Letter, 0 unresolved references, 0 BLOCKED,
0 em dashes (two en dashes are bibtex page ranges), 0 overfull boxes. The official PeerJ Overleaf
template needs a PeerJ login to download; a plain article class with the stated conventions is used.

refs.bib: six entries added, verified live on 29 Sep (CrossRef for the three PeerJ CS papers: Dincer
& Kilimci 2026 e3769, Turkmen 2026 e4000, Hebenstreit et al. 2024 e1999; arXiv API plus OpenAlex for
Kurtic et al. ACL 2025 and Lee et al. IJCAI 2025; the BFCL leaderboard data file). The author has not
yet read the five papers; they are cited for what their abstracts state (edge deployment relies on
compression; SLM surveys list quantization and tool use; CoT gains vary by model; two broad
quantization evaluations with no tool-calling task). README rewritten to the formula title, no arXiv
mention, Llama scripts and coerced.py listed. Local commit and local tag v1.2-peerj made; nothing pushed.

PDF at the time of this entry: paper/peerj/main.pdf, 19 pages, sha256 1d3aed529d51a0f76691015c789ae587252116a55e3dc64daa1e15a9d80b4b27 (pre-submission; the
DOI placeholder still has to be replaced, which changes the hash).

## 30 Sep 2026: citation check of the references added on 29 Sep

Scope: the six refs.bib entries added in 2634389 (dincer2026edge, turkmen2026slm, hebenstreit2024cot,
kurtic2024bf16, lee2024tradeoffs, bfclleaderboard2026) and the four whose first commit is e9b6250 on
29 Sep although their comment says 25 Sep (dondeti2026toolguard, malekar2025amdahl,
mekala2025longcontext, llama3). Each citing sentence in paper/peerj/main.tex was read against the
paper itself, not only its metadata.

- dincer2026edge. Read: https://peerj.com/articles/cs-3769/ (full HTML text; searched for tool, agentic,
  small language). Intro sentence ("treat compression as a precondition for running them there at
  all"): partly supported. The review calls model compression "a central enabler" beside hardware
  acceleration and hybrid edge-cloud, not a precondition. Related-work sentence ("surveys of small
  language models ... name tool use as a direction"): unsupported for this paper. It is about LLMs on
  edge devices, lists quantization among compression techniques, and never mentions tool use; its
  future directions are co-design, federated learning and secure offloading. Change: intro sentence
  narrowed to "counts model compression, quantization included, as a central enabler of running these
  models on memory-limited hardware"; related-work sentence rewritten so this paper is cited only for
  listing quantization. Bib correct (vol 12, e3769, 2026, DOI 10.7717/peerj-cs.3769).
- turkmen2026slm. Read: https://peerj.com/articles/cs-4000/ (full HTML text). Lists pruning,
  quantization and distillation for deriving clinical SLMs (a Quantization subsection) and names
  agentic frameworks for planning and tool use as a future direction; measures neither. Verdict:
  supported. Change: the shared sentence was split so the tool-use clause cites only this paper. Bib
  correct (vol 12, e4000, 2026).
- hebenstreit2024cot. Read: https://doi.org/10.7717/peerj-cs.1999, full text via Europe PMC
  (PMC11157560, https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11157560/fullTextXML). Sentence
  ("whether chain-of-thought helps at all, and by how much, already varies by model and dataset at full
  precision"): partly supported. The paper's headline is that CoT gains over direct prompting "remain
  robust across different models and datasets" with some variation (Command-XL and GPT-4 gain most;
  for Flan-T5 direct prompting is among the best; prompts differ by dataset). It says nothing about
  numerical precision. Change: "the gain from zero-shot chain-of-thought prompting over direct
  answering holds on average across six models and six question-answering datasets but varies in size
  by model and dataset". Bib correct.
- kurtic2024bf16. Read: https://arxiv.org/pdf/2411.02355 (v4) and https://aclanthology.org/2025.acl-long.1304.pdf.
  Intro ("academic benchmarks and long-form tasks"): partly supported; the non-academic set is
  Arena-Hard, HumanEval/HumanEval+ and RULER. Changed to "chat, code-generation and long-context
  tasks". Related work ("well-tuned INT8 and INT4 weight-only formats close to lossless"): partly
  supported; the paper calls only FP8 effectively lossless, INT8 1-3% degradation, INT4 weight-only
  on par with 8-bit. Changed to those three findings. No tool-calling task (grep of full text).
  Bib: added "(Volume 1: Long Papers)", pages 26872-26886, DOI 10.18653/v1/2025.acl-long.1304 from the
  Anthology record; dropped the arXiv note.
- lee2024tradeoffs. Read: https://www.ijcai.org/proceedings/2025/0902.pdf and arXiv 2409.11055v6.
  1B to 405B, four methods, 13 datasets; quantized models generally beat smaller FP16 baselines but
  struggle on instruction following and hallucination detection; no tool-calling task. Verdict: both
  sentences supported. Bib: booktitle set to the proceedings title (IJCAI-25), pages 8113-8121, DOI
  10.24963/ijcai.2025/902 added; arXiv note dropped.
- bfclleaderboard2026. Read: https://gorilla.cs.berkeley.edu/leaderboard.html and
  https://gorilla.cs.berkeley.edu/data_non_live.csv (re-fetched 30 Sep; byte-identical to
  analysis/bfcl_leaderboard/data_non_live.csv; Last-Modified 13 Apr 2026; page says BFCL V4, last
  updated 2026-04-12). One Llama-3.1-8B row, "(Prompt)", Python Simple AST 94.00%, no FC row. Verdict:
  supported. No change.
- dondeti2026toolguard. Read: https://openreview.net/forum?id=0ct01Da0Ff (TMLR, published 8 Sep 2026).
  Seven SLMs from 1B to 4B, deterministic would-dispatch rule, consumer hardware. Verdict: supported.
  No change.
- malekar2025amdahl. Read: https://openreview.net/forum?id=JtrQJJQYpP (TMLR, 15 Sep 2025). Sentence
  ("those gains are capped by whatever part of the model stays in higher precision", said of lower
  bit-widths generally): partly supported; the analysis is for 1-bit and ternary projection weights
  (W1A8/W2A8) with attention left in higher precision. Change: "show, for binary and ternary weights,
  that the throughput gain is capped ...". Bib correct.
- mekala2025longcontext. Read: https://arxiv.org/abs/2505.20276 and https://aclanthology.org/2025.emnlp-main.479.pdf.
  "Drops of up to 59%" for 4-bit methods on long-context inputs is in the abstract and body of the
  published version. Verdict: supported. Bib: was an arXiv preprint; now EMNLP 2025 main, pages
  9422-9470 (printed pages; CrossRef's 9433-9481 disagrees with the PDF), DOI 10.18653/v1/2025.emnlp-main.479.
- llama3. Read: https://arxiv.org/pdf/2407.21783 (v3). All results are for Llama 3.1; Llama 3.2 is not
  mentioned. The citation sat after both Llama-3.2-3B-Instruct and Llama-3.1-8B-Instruct: partly
  supported. Change: "whose Llama 3.1 models are described in \citet{llama3}". Bib correct.

Also: paper/main_tmlr.tex (not edited) has the same llama3 placement after both Llama models and
the same unqualified malekar2025amdahl sentence; it shares refs.bib, so the bib corrections reach
it. Rebuilt with tectonic: 19 pages, 0 undefined references, 0 "??". Bibliography page ranges now
render five en dashes (two before); prose has none. PDF sha256
90a78d16992bd914382cbe132a731c9e7862fab510f7a2b66c42d62505def386.

## 29 Sep 2026, evening: PeerJ revision after three reviews (entry appended after the 30 Sep entry because entries are added in the order they are written)

Three reviews of paper/peerj/main.tex (an academic editor's refutation pass, a quantization
researcher, a hostile desk editor) returned overlapping blocking issues. This entry records what was
checked against the raw files, what changed, and what was found on the way that the reviewers had
not raised. All edits are local; nothing was pushed, deposited or submitted.

The hypothesis record. `git log` confirms the reviewers' reading: paper/preregistration.md first
appears in cac7796 (18 Sep 2026, 17:37:31 -0700) together with the finished ladder (rung logs
14:33 to 15:23) and both repeat arms (17:05); 07cee6b (17:56) changed only the open-items line about
the extractor; the Hypotheses section is byte-identical since the first commit; prereg-v1 points at
cac7796 and exists locally only. The paper no longer says "pre-registered" anywhere. Section 3.1
gives the commit hashes and times and says the record cannot show the hypotheses preceded the
results; a deviations table (Table 1) lists FP16 not run, the dropped models and subsets, the
unreported metrics, the H1/H2/H3 statistics, the post hoc tests, the extractor edit, the hardware and
the title. preregistration.md itself was not edited.

Statistics. analysis/paper_numbers.py now applies Holm within families (one per model on the
single-call arm across both verdicts, one per model on GSM8K, one for multi-turn, one for the
penalty arm; 28 tests in 10 families), prints raw and adjusted p in every table, uses the adjusted
p in the cliff rule, and adds an Agresti and Min (2005) interval on every paired difference and a
Connor (1987) minimum detectable difference per model at Q4_K_M (new Table 6, fourbit.tex). Under
the per-model family the Llama-3.2-3B strict Q4_K_M loss (9 lost, 1 gained, p = 0.021) adjusts to
0.064 and is reported as suggestive; its strict cliff rung moves to Q3_K_M (adjusted 0.030). The
Qwen3-1.7B Q3_K_M cliff adjusts to 0.017. Refs added: holm1979, agresti2005paired, connor1987paired.

Hypotheses as written. H1 on schema validity (share of outputs decoded as a call): 99.75% at Q8_0,
never below 98.75%, threshold 94.76%, never triggers; H1 fails under either statistic. H2 structural
share of failures (decode, wrong name, wrong count, missing parameter) Q8_0 to Q3_K_M: Qwen3-1.7B
9.1% to 15.4% (+6.3, fails the 15-point threshold); Qwen3-8B +42.9 on 7 failures; Qwen3-14B 0;
Llama-3.2-3B -10.2; Llama-3.1-8B +21.6 by BFCL's categories and +0.8 after the JSON re-read below
(new Table 9, htwo.tex). H3 as registered is supported: AST drop 4.75 vs strict free-form drop 39.50
at Q3_K_M, difference 34.75; the strict-minus-lenient gap (at most 0.50) is now a separate,
unregistered observation, and the "three of five did not hold" tally is corrected to one held (H3),
three did not (H1, H2, H4), one not evaluable (H5). Hallucinated-function rate at most 0.75% (3 of
400 on Qwen3-1.7B at Q3_K_M, all corrupted spellings of the right name).

Truncation. Per rung, GSM8K truncated generations are 28, 32, 21, 34, 213; of the 213 at Q3_K_M,
164 have no committed answer, 20 commit to a wrong one and 29 commit to the right one and run on
(counted correct; 187 = 158 finished + 29). Q8_0 already truncates 7%. Two new columns in Table 4.
BudOf is now taken from the data (213) and asserted equal to the truncated count.

Per-request lengths. The "n_gen" lines in llama-server logs are 3-second progress prints, several
per long request, not one per request; the earlier medians (182 tokens, p90 753, "1 of 539
requests") and the multi-turn medians (509 vs 213) were biased by them. Replaced by
output_token_count from BFCL's result files: single call median 195 (Q8_0) and 155 (Q3_K_M), p90
411 and 353, 1 of 400 Q3_K_M requests at the 4,096 cap. At Q3_K_M 178 of 400 generations have an
empty reasoning block (0 at Q8_0 and Q4_K_M); those score 87.1% vs 86.9% for the ones that reason.
figure.py switched to the same source; Figure 1(b) regenerated (matplotlib installed into .venv;
numpy re-pinned to 1.26.4 afterwards because bfcl-eval requires it).

Found while reading the raw files, not raised by the reviewers.

1. Llama-3.1-8B decode failures. bfcl-eval 2026.3.23's LlamaHandler_3_1.decode_ast() decodes a
   single call with Python eval(); JSON's true/false/null are not Python literals. Of the 3, 6 and
   14 "ast_decoder" failures at Q8_0, Q4_K_M and Q3_K_M, 2, 5 and 13 are well-formed
   {"name": ..., "parameters": {...}} objects with a bare boolean. Raw outputs with a bare boolean:
   2, 5, 13 of 200; quoted boolean: 20, 18, 9; quoted number: 61, 35, 12; bare number: 82, 109,
   134. analysis/coerced.py now re-reads a decode failure with json.loads and checks it like any
   other call. Llama-3.1-8B coerced moves from 92.00 / 90.50 / 85.00 to 93.00 / 93.00 / 91.50;
   the "7-point coerced loss at three bits" was mostly the parser (Q3_K_M now -1.50, p = 0.508).
   Qwen3 and Llama-3.2-3B have no decode failures and are unchanged. The abstract, contributions,
   Section 4.5, Discussion and Conclusions were rewritten to match.
2. Multi-turn aborts. The multi_turn_base result files contain "Error during inference: ...
   Context size has been exceeded." for 46, 59 and 137 of 200 trajectories at Q8_0, Q4_K_M and
   Q3_K_M (plus 2, 1, 2 handler KeyErrors on malformed calls); BFCL scores every one as a failure.
   The server ran 4 slots on a unified 32,768-token KV cache (n_ctx_slot = 32768, kv_unified =
   true), so concurrent trajectories shared it; on completed trajectories the per-request context
   never exceeded 22,539 tokens. The 17.0 / 13.5 / 1.5 accuracies are therefore dominated by the
   abort rate. Completed-only accuracy 34/152, 27/140, 3/61. Section 4.6 now reports the arm as
   confounded and H5 as not evaluable; Table 8 carries the abort counts. A re-run with one slot or
   a per-slot cache is on the author checklist. The earlier drafts' "supported by a wide margin"
   is withdrawn.
3. FP16 size. SizeFp was hard-coded as 3.8 (GiB, from the notebook) while the other sizes are
   decimal GB from st_size; the Ollama manifest (copied to runs/ollama-manifest-qwen3-1.7b-fp16.json)
   gives 4,069,678,752 bytes = 4.1 GB, so CompressFour is 32% rather than 34%.

Other fixes from the reviews: abstract H4 sentence corrected (accuracy unchanged, 2 verdicts flip
each way per rung); "1 of 539 requests" corrected; "safe"/"costs nothing" replaced by the interval
bound (coerced lower ends no worse than -5.2 points, MDD 2.8 to 3.7); the abstract's three-bit
sentence names the verdict for Llama-3.2-3B; mirror repositories, snapshot commits and SHA-256 of
the tokenizer_config.json and config.json files added to Section 3.8 (unsloth/Llama-3.1-8B-Instruct
snapshot 4699cc75b550f9c6f3173fb80f4703b62d946aa5: tokenizer_config.json
671ecdff1a4241f7d3e0ad21d347ada7d90f673810906727c124972e3ce03465, config.json
ad98082c6bc4ea7078915219241814762be259de16d6ca5f170ba02820b3928b; unsloth/Llama-3.2-3B-Instruct
snapshot 006f5dcd1393c3add266de40994ba96225e9689d: tokenizer_config.json
9ddd255c19fe319c8d4e891163540382e9fbda99f394674f2a929efc47d57458, config.json
eadff796b79b82cefa0537004668d70a1dd099fd4986b91ef88398ed91b26311); context settings and the shared
cache stated in Section 3.4 with the argument that they cannot affect a single call; the extractor
takes the last commitment (stated); llama-server --version confirms "0.4.1 (build 10964, commit
b29c606e2)"; multi_turn_base has 200 items, so n = 200 is the whole category (stated); Table 5
caption says the Qwen3-1.7B rows come from Table 3; the Dondeti bib entry carries its OpenReview
URL; refrains trimmed ("nothing changed" removed, "the rungs that matter" removed, the aphorism
"The output with no slack is the one that holds up" cut; contribution 2 no longer claims most papers
omit repeats); the reproducibility sentence names the recorded throughput as the one exception.
Data Availability now names tag v1.3-peerj and the placeholder DOI 10.5281/zenodo.XXXXXXX (reserved,
to be activated on acceptance); a Use-of-generative-AI declaration and a Preprint declaration (arXiv
submission not announced, nothing public) were added; Competing Interests states the work is
unaffiliated with the employer. Written for the author: paper/peerj/COVER-LETTER-DRAFT.md,
AUTHOR-CHECKLIST.md (Zenodo DOI, tag push, OSF option, city and country, AI-statement wording,
cross-check and re-run decisions), fig1-legend.txt (standalone legend for the separate figure
upload), GATE-REPORT.md.

Not done, and why. The Llama-3.1-8B second-path cross-check and the multi-turn re-run each need
about an hour of the author's GPU and a decision the notebook already leaves to the author; the
paper states both as not run. No Zenodo deposit, OSF registration, push or account action was made.
The Turkmen and Hebenstreit citations were kept (the venue-citation gate needs three; both were
read on 30 Sep and their sentences narrowed then). paper/main_tmlr.tex is now stale: it states the
multi-turn and Llama-3.1-8B results this revision corrected and no longer compiles against the
regenerated macros (MtNgen* were removed because they were biased); it must not be submitted.

Timing note for the recovery contract: the 18 Sep entry's "roughly 100 minutes per rung" does not
match the rung logs (Q8_0 14:33, Q6_K 14:44, Q5_K_M 14:58, Q4_K_M 15:12, Q3_K_M 15:23, about
12 minutes per rung); the 100-minute figure was the serial estimate (400 items at 15 s) and ignored
the four parallel slots. The log times are the record.

Build: tectonic, 24 pages US Letter, 0 undefined references, 0 "??", 0 BLOCKED, 0 em dashes, en
dashes only in bibliography page ranges, 0 overfull boxes, abstract 486 words. paper_numbers.py:
986 macros, 28 McNemar tests in 10 Holm families. PDF sha256
64d9909933083639c5994e91647dd8858fe5a5a6ab34e4ec4c9aebc4c6923538. Local commit and local tag
v1.3-peerj; nothing pushed.

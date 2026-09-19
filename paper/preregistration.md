# Pre-registration: where the quantization precision floor sits for agentic tool calling

Status: hypotheses and thresholds fixed 18 Sep 2026 before the first grid run. The Kurt and Lotfi
full-text sections were appended during the first rung as documentation; no hypothesis or threshold
was edited after runs began. Committed at the first commit of this repository.
Novelty check on the k-quant/tool-calling gap: DONE 18 Sep 2026, gap confirmed open (see below).

Author: Akshay Kumar (independent). Working title: *The Schema Breaks First: Quantization Floors
for Agentic Tool Calling*. Target: arXiv preprint, then an ML-systems or evaluation venue.

## Question

Post-training quantization is how language models reach laptops, and tool calling is what agents
on laptops do. Published measurements of quantization damage are taken on free-form tasks: math,
code and science question answering, scored by extracting a final answer from prose. Structured
tool calling is a different regime. The output must satisfy a schema, there is no semantic slack
in a function signature, and a call is either well formed or it is not.

Two questions follow. At which bit-width does schema compliance break, relative to where free-form
accuracy breaks on the same model? And how much of the published free-form degradation is the
answer extractor rather than the model?

## Why tool calling answers the second question

Lotfi et al. (arXiv 2606.00206, May 2026) report that in up to 52% of quantization-induced
failures the model reaches the correct answer in its intermediate reasoning but does not emit it
as the final answer, alongside chain-of-thought inflating from 5.2K to 23.4K tokens on a 1.5B
model. That measurement depends on extracting a final answer from free text, and a separate line
of work finds extreme verbosity burying answers in roughly 31% of extraction failures.

The Berkeley Function Calling Leaderboard scores with a deterministic abstract-syntax-tree matcher
against a reference invocation. There is no extractor to confound. Measuring the same models on
both settings bounds the extraction contribution without re-litigating anyone's analysis.

## Closest prior work, checked in full text on 18 Sep 2026

Kurt, *Which Quantization Should I Use? A Unified Evaluation of llama.cpp Quantization on
Llama-3.1-8B-Instruct* (arXiv 2601.14277, Jan 2026, single author) is the nearest neighbour and the paper this
one extends. They quantize one model, Llama-3.1-8B-Instruct, into 13 GGUF configurations
(Q3_K_S/M/L, Q4_0, Q4_1, Q4_K_S, Q4_K_M, Q5_0, Q5_1, Q5_K_S, Q5_K_M, Q6_K, Q8_0) against an FP16
baseline, and score them on GSM8K, HellaSwag, IFEval, MMLU, TruthfulQA and WikiText-2 perplexity,
plus CPU throughput, size and quantization time.

A full-text read on 18 Sep 2026 found no mention of tool calling, function calling, agentic tasks,
structured output, JSON generation or schema compliance anywhere in that paper. Every task they
score is free-form or multiple choice. Their conclusion states: "Future work should extend the
same protocol across additional model families and sizes, diverse hardware targets, and
longer-context regimes."

This paper does that, and adds the axis they omit. We adopt their format ladder so the numbers are
directly comparable, extend it across model families and sizes as they propose, and score the one
thing an agent actually does.

## Lotfi et al., read in full on 18 Sep 2026

*Quantized Reasoning Models Think They Need to Think Longer, but They Do Not* (arXiv 2606.00206,
May 2026). Five reasoning models from 1.5B to 32B: DeepSeek-R1-Distill-Qwen 1.5B/7B/14B,
DeepSeek-R1-Distill-Llama 8B, QwQ-32B. Quantization by GPTQ and AWQ at 3 and 4 bits (group 128)
plus FlatQuant W4A4KV4 and W8A8KV8. Benchmarks GSM8K, MATH-500, AIME-120, LiveCodeBench and
GPQA-Diamond.

Three details shape this paper's position.

1. Their quantization methods are research methods. None is a llama.cpp k-quant, which is what
   ships to laptops. The deployed ladder is unmeasured by them.
2. Their failure categorisation, including the overthinking class that carries the 52% figure,
   uses GPT-5 as an LLM judge over manual annotation. BFCL scores by deterministic AST matching,
   so our measurement has no judge anywhere in it.
3. They state their own scope: the overthinking marker list is "manually curated for English
   reasoning models" and evaluation "focuses on math, coding, and science benchmarks". Whether
   the penalty preserves schema compliance is open by their own admission.

H4 therefore tests a fix whose authors have already said it is untested outside free-form English
reasoning. A null result there is informative and is reported either way.

## What is new here

Existing quantization evaluations cover perplexity, prose, code quality, mathematical reasoning
and, in one case, package hallucination in shell commands. Multilingual degradation under
quantization is already well covered and is explicitly out of scope. We found no study measuring
schema compliance on an agentic tool-calling benchmark across a precision ladder.

We also measure the ladder practitioners actually deploy. Published work uses research
quantization methods; laptop deployments run llama.cpp k-quants, and Ollama defaults to Q4_K_M.
Nobody has published that curve for tool calling.

## Design

Grid: model x quantization level x task type, all generations logged in full.

- Quantization ladder: the subset of arXiv 2601.14277's ladder that spans the range, Q8_0, Q6_K,
  Q5_K_M, Q4_K_M, Q3_K_M, built from the same FP16 source per model so the ladder is controlled.
  FP16 is the reference arm. Using their format names keeps the two papers comparable.
- Models: at least one shared with Lotfi et al. for comparability (DeepSeek-R1-Distill-Qwen-1.5B
  and 7B), one tool-calling-native family across sizes (Qwen3 at 1.7B, 4B, 8B, 14B), and
  Llama 3.1 8B as a common reference point.
- Structured task: BFCL v4, run locally, reporting the non-live, live and multi-turn subsets
  separately. Deterministic AST matching throughout; no LLM judge anywhere in the pipeline.
- Free-form control: one mathematics set scored by regex extraction, and the same generations
  re-scored under a lenient hierarchical extractor. The gap between the two is the extraction
  contribution.

Metrics: AST accuracy; schema validity rate, meaning the output parses as a call at all;
hallucinated-function rate; argument type-error rate; output length in tokens; and wall-clock
latency, which costs nothing to record and is what deployment decisions actually turn on.

## Hypotheses

H1 (the schema breaks first). Schema validity falls below 95% of its fp16 value at a higher
bit-width than free-form accuracy does on the same model. Threshold: the two floors differ by at
least one rung of the ladder on a majority of models tested.

H2 (failure mode shifts). As precision falls, the dominant BFCL failure category moves from
wrong-argument-value toward invalid-call and hallucinated-function. Threshold: the share of
failures that are structural rather than semantic rises by at least 15 percentage points between
Q8_0 and Q3_K_M.

H3 (bounding the extractor). On the same models and precision levels, the accuracy drop measured
by deterministic AST matching is smaller than the drop measured on the free-form set under strict
regex extraction. Threshold: a difference of at least 5 points, which would put a floor under how
much of the published free-form degradation is extraction rather than model.

H4 (does the published fix transfer). The training-free logit penalty on overthinking markers
reported to cut chain-of-thought by 12 to 23% while preserving accuracy does not preserve schema
compliance. Threshold: schema validity under the penalty falls by at least 3 points relative to
the same model and quantization level without it. A null here is equally publishable and is
stated as such.

H5 (multi-turn amplification). Degradation on BFCL multi-turn trajectories exceeds degradation on
single-turn calls at the same precision. Threshold: at least twice the relative drop.

## What would falsify the paper's premise

If schema compliance and free-form accuracy degrade at the same bit-width, H1 fails and there is
no schema cliff. The deployment table is still the deliverable, and the paper reports a negative
result with the same instrument. This is stated now so that the negative outcome cannot be
reframed later.

## Deliberate exclusions

Multilingual degradation, already covered by at least three papers with contested findings.
Quantization method comparison (AWQ, GPTQ, SmoothQuant); we measure one ladder, the deployed one,
and say so. Training-time quantization. Models above what the hardware holds at useful precision.

## Hardware and budget

MacBook Pro M1 Pro, 16 GB, for everything up to 14B at Q4_K_M. Larger arms, if run at all, on a
single rented GPU against remaining cloud credit. No paid API calls anywhere in the design; every
number comes from local inference, which is also what makes the artifact reproducible by a reader
with a laptop.

## Artifact

Harness, quantization build scripts, every raw generation, per-cell result CSVs and one summary
table, released under a permissive licence at the tag the paper describes, reproducible with one
command.

## Open items before freezing

- Confirm BFCL v4 runs locally against an Ollama or llama.cpp endpoint without modification.
- Read Lotfi et al. in full, not the abstract, and confirm the extraction method they used.
- Decide the free-form control set and fix its extraction rules before any generation runs.

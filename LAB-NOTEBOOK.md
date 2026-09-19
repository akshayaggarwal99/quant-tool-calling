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

# Post-Training k-Quantization and Agentic Tool-Calling Accuracy on Five Qwen3 and Llama Models

Code, run logs and raw generations for the paper *Post-Training k-Quantization and Agentic Tool-Calling Accuracy on Five Qwen3 and Llama Models* (Akshay Kumar, 2026).

The question: at what bit-width does llama.cpp k-quant quantization break an agent's tool calls, and does it break them before or after it breaks free-form reasoning on the same weight files?

The answer, for Qwen3-1.7B: both floors sit at Q4_K_M, but the tool call loses about 5 points at Q3_K_M where free-form math loses about 40, because three-bit weights make the chain of thought run past its token budget and a tool call is over long before that happens. No cliff at 8B or 14B. On the Llama family the strict schema score moves in both directions under quantization because compression changes how the models type their arguments (Llama-3.1-8B at Q8_0 writes numbers as quoted strings, which the strict checker rejects, and at Q3_K_M writes bare JSON booleans, which the BFCL handler's Python `eval()` refuses); scored on the parsed value, neither Llama model shows a detectable loss at four or three bits. The multi-turn arm (17% to 1.5% at three bits) is confounded: 46, 59 and 137 of 200 trajectories aborted on a KV cache shared by four server slots, and it has to be re-run with a per-trajectory context.

## What is here

| Path | Contents |
|---|---|
| `paper/` | LaTeX source (`peerj/main.tex` is the current manuscript; `main_tmlr.tex` and `main.tex` are earlier versions that predate the 29 Sep revision and no longer compile against the regenerated tables), `preregistration.md` (the hypothesis file, dated 18 Sep 2026; its first commit, cac7796 at 17:37 that day, postdates the first ladder, so the paper does not call it a pre-registration), figure and generated tables |
| `analysis/paper_numbers.py` | Recomputes every number in the paper from `runs/` and writes `paper/tables/*.tex`. Nothing in the paper is typed by hand |
| `analysis/coerced.py` | The type-coerced secondary tool-calling score: each strict BFCL failure re-checked by BFCL's own checker after quoted arguments are parsed to the schema's type, and each decode failure re-read as JSON when it is one well-formed call; also the failure classification (structural vs semantic) |
| `analysis/bfcl_leaderboard/` | The public BFCL V4 leaderboard data files used for the Llama-3.1-8B comparison, with the fetch record |
| `analysis/figure.py` | Figure 1 |
| `runs/` | BFCL result and score files for every rung and model, GSM8K generations, the 16K budget re-run, `llama-server` logs, and the reproducibility repeats |
| `run_*.sh` | The scripts that produced each arm (see below) |
| `gsm8k_gen.py`, `gsm8k_score.py` | Free-form control: generation and the strict / lenient extractors |
| `LAB-NOTEBOOK.md` | Dated log of every run, failure and decision |

## Reproducing

Requirements: llama.cpp (`llama-server`, `llama-quantize`), Python 3.12, the `bfcl-eval` package (pinned in the `.venv` setup below), an Apple Silicon or CUDA machine.

```bash
python3 -m venv .venv && .venv/bin/pip install bfcl-eval datasets
./run_ladder.sh      # builds Q8_0..Q3_K_M from the FP16 GGUF and scores simple_python
./run_repeats.sh     # Q8_0 and Q4_K_M three times each
./run_gsm8k.sh       # free-form control, 400 GSM8K questions per rung
./run_budget.sh      # the truncated Q3_K_M generations re-run at 16,384 tokens
./run_h4.sh          # overthinking-marker logit penalty
SUBSET=1 ./run_model.sh qwen3:8b-fp16  Qwen/Qwen3-8B-FC  Qwen3-8B  Q8_0 Q4_K_M Q3_K_M
SUBSET=1 ./run_model.sh qwen3:14b-fp16 Qwen/Qwen3-14B-FC Qwen3-14B Q8_0 Q4_K_M Q3_K_M
CATEGORY=multi_turn_base ./run_model.sh qwen3:1.7b-fp16 "Qwen/Qwen3-1.7B-FC" Qwen3-1.7B Q8_0 Q4_K_M Q3_K_M
./run_llama.sh       # second family: Llama-3.2-3B and Llama-3.1-8B, three rungs, BFCL n=200 and GSM8K x400 (calls run_model.sh and run_gsm8k_model.sh)
.venv/bin/python analysis/paper_numbers.py && .venv/bin/python analysis/figure.py
```

The FP16 sources are the `*-fp16` Ollama blobs; `run_ladder.sh` and `run_model.sh` locate the blob and quantize it. Weight files are not committed. The Llama runs load the tokenizer and configuration from the ungated `unsloth/` mirrors of the gated `meta-llama` repositories (`REMOTE_OPENAI_TOKENIZER_PATH` in `run_llama.sh`).

Every script is resumable: a rung that already has a score directory is skipped.

## Citation

```bibtex
@unpublished{kumar2026quant,
  title  = {Post-Training k-Quantization and Agentic Tool-Calling Accuracy on Five Qwen3 and Llama Models},
  author = {Kumar, Akshay},
  year   = {2026},
  note   = {Manuscript, September 2026, tag v1.3-peerj. Code and data: https://github.com/akshayaggarwal99/quant-tool-calling}
}
```

MIT licence.

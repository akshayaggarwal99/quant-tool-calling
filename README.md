# The Schema Holds Where the Reasoning Collapses

Code, run logs and raw generations for the paper *The Schema Holds Where the Reasoning Collapses: Quantization Floors for Agentic Tool Calling* (Akshay Kumar, 2026).

The question: at what bit-width does llama.cpp k-quant quantization break an agent's tool calls, and does it break them before or after it breaks free-form reasoning on the same weights?

The answer, for Qwen3-1.7B: both floors sit between Q4_K_M and Q3_K_M, but the tool call loses about 5 points where free-form math loses about 40, because three-bit weights make the chain of thought run past its token budget and a tool call is over long before that happens. No cliff at 8B or 14B. Multi-turn tool calling at three bits collapses from 17% to 1.5%.

## What is here

| Path | Contents |
|---|---|
| `paper/` | LaTeX source, `preregistration.md` (hypotheses frozen 18 Sep 2026, before the first run), figure and generated tables |
| `analysis/paper_numbers.py` | Recomputes every number in the paper from `runs/` and writes `paper/tables/*.tex`. Nothing in the paper is typed by hand |
| `analysis/figure.py` | Figure 1 |
| `runs/` | BFCL result and score files for every rung and model, GSM8K generations, the 16K budget re-run, `llama-server` logs, and the reproducibility repeats |
| `run_*.sh` | The scripts that produced each arm (see below) |
| `gsm8k_gen.py`, `gsm8k_score.py` | Free-form control: generation and the strict / lenient extractors |
| `LAB-NOTEBOOK.md` | Dated log of every run, failure and decision |

## Reproducing

Requirements: llama.cpp (`llama-server`, `llama-quantize`), Python 3.11+, the `bfcl-eval` package (pinned in `.venv` setup below), an Apple Silicon or CUDA machine.

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
.venv/bin/python analysis/paper_numbers.py && .venv/bin/python analysis/figure.py
```

The FP16 sources are the `qwen3:*-fp16` Ollama blobs; `run_ladder.sh` locates the blob and quantizes it. Weight files are not committed.

Every script is resumable: a rung that already has a score directory is skipped.

## Citation

```bibtex
@article{kumar2026schema,
  title   = {The Schema Holds Where the Reasoning Collapses: Quantization Floors for Agentic Tool Calling},
  author  = {Kumar, Akshay},
  year    = {2026},
  note    = {arXiv preprint}
}
```

MIT licence.
